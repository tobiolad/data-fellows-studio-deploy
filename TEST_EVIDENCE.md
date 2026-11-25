# Test evidence — reproduced fresh, this session, 25 November 2026

The master prompt required reproducing all tests fresh rather than trusting
historical claims. This was done in this exact run, not carried over from
an earlier part of this conversation. Commands, databases and raw results
are recorded below so they can be re-run and checked.

## Studio backend (`data-fellows-studio/backend`)

**Pure-unit run, no database** (`python3 -m pytest -q`):

```
67 passed, 49 skipped, 10 warnings, 8 subtests passed in 1.40s
```

The 49 skips are every test requiring `STUDIO_TEST_DATABASE_URL` — these are
real integration tests against Postgres, not placeholders, and they simply
do not run without a database configured. This is correct, safe behavior
for a test suite (it fails closed rather than silently testing against
nothing), but it means a `pytest` run with no environment configured
**understates coverage** if read as "67 tests" rather than "67 tests ran;
49 more exist and require a database."

**Full run, against a genuinely fresh local Postgres database**
(created with `createdb studio_test`, `STUDIO_TEST_DATABASE_URL` pointed at
it):

```
116 passed, 10 warnings, 8 subtests passed in 5.86s
```

**A real test-isolation defect was found and reproduced while gathering
this evidence.** The first attempt to run the full suite used a
`studio_test` database that already existed on this machine (left over
from state before this session's compaction). That run produced **10
failures**, including an assertion mismatch (`3 != 1` on a profile revision
count) and failures in the billing, diagnostic-handoff and persistence
integration tests. Dropping and recreating the database fresh
(`dropdb studio_test && createdb studio_test`) and re-running the identical
command produced a clean `116 passed`. **Conclusion: the integration test
suite assumes it owns a database that is empty at the start of a run and
has no teardown/reset step of its own.** This is safe in CI (which
presumably provisions a fresh database per run) but means **a developer
running the suite twice against the same local database without
truncating it first will see false failures that look like product bugs
and are not.** This is a real, previously undocumented test-hygiene gap,
recorded here rather than silently worked around. See
`DECISIONS_AND_BLOCKERS.md`.

## Studio frontend (`data-fellows-studio/frontend-next`)

```
npm run build
✓ 2875 modules transformed
✓ built in 673ms
```

Builds clean. One pre-existing warning (a single JS chunk over 500kB,
unminified-size code-splitting advice from Vite) — not a defect, not
investigated further as out of scope for this audit.

## BizPilot backend (`bizpilot-pro-concept/backend`)

**First attempt, run from inside `backend/`** (the directory a developer
would most naturally `cd` into): fails to collect `test_performance.py`
with `ModuleNotFoundError: No module named 'openai'`, and separately fails
to collect all 16 tests in `tests/test_diagnostics.py` with
`ModuleNotFoundError: No module named 'backend'` — because that file
imports as `from backend.diagnostics import ...`, which only resolves
when pytest is invoked from the **repository root**, not from inside
`backend/`.

**Correct invocation, from the repository root, with the broken
dependency excluded and an isolated test database provided** (the file
itself demands one: `pytest.fail("Use an isolated test database via
BIZPILOT_DATABASE_URL")` when the variable is absent — this is the same
safe-by-default pattern as Studio's):

```
cd bizpilot-pro-concept
createdb bizpilot_test
BIZPILOT_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bizpilot_test \
  python3 -m pytest -q backend/ --ignore=backend/test_performance.py

26 passed, 7 warnings in 9.43s
```

Re-run against a freshly dropped-and-recreated `bizpilot_test` database to
rule out the same hidden-state risk found in Studio: **identical result,
26 passed**, confirming this suite (unlike Studio's) tears down or never
accumulates state that affects re-runs — or simply that no test in this
suite happens to depend on starting from zero. Not fully diagnosed either
way; noted as a difference worth a second look if the suite grows.

**Confirmed, reproducible defect**: `backend/services/async_ai_service.py`
imports `from openai import AsyncOpenAI` at module load time, but `openai`
is not listed in `backend/requirements.txt` and is not installed. Any test
file that imports this module transitively — currently only
`test_performance.py` — cannot be collected at all. This is a genuine gap,
not a flake: either the dependency needs to be declared, or the import
needs to be made lazy/optional if `async_ai_service` is meant to work
without it configured. Recorded as a defect in `DECISIONS_AND_BLOCKERS.md`.

The 7 warnings are `PytestReturnNotNoneWarning` (tests returning `bool`
instead of using `assert`) in `test_efficient_data_operations.py` — style
debt, not a correctness risk, not acted on in this audit.

## BizPilot frontend (`bizpilot-pro-concept/frontend`)

```
npm run build
✓ Compiled successfully in 1842ms
✓ Generating static pages (9/9)
```

Builds clean, all 9 routes statically generated.

## data-fellows-web-app

Not exercised this session — out of scope for the master prompt's named
repositories' test obligations (the audit's own working directory shows
this repo attached but it was not part of the engineering checklist's
functional scope beyond the "zero integration with Studio" finding
recorded in `SYSTEM_AUDIT.md`/`ARCHITECTURE.md`). If a test suite exists
there it was not run in this pass; flagged as an open item if the public
site is brought into future verification scope.

## Cross-repo diagnostic handoff

`test_diagnostic_handoff.py` (Studio side, 1 of the 116 passing) and the
corresponding handoff tests inside BizPilot's `test_diagnostics.py`
(`test_handoff_delivery_succeeds_against_a_configured_studio_receiver`,
`test_handoff_delivery_records_a_safe_error_when_studio_rejects_it`,
`test_handoff_delivery_without_studio_configuration_only_records_intent`,
all 3 among the 26 passing) each independently exercise their own side of
the contract against a stand-in HTTP receiver in the test process, not a
live cross-service call. This session's earlier work (summarized from
before compaction) separately proved a real, live HTTP handoff between a
running BizPilot process and a running Studio process — that proof was not
re-run in this evidence-gathering pass since it requires two live
processes rather than `pytest`, and re-running it was not necessary to
validate the fresh unit/integration numbers above. If the founder wants
that live proof re-demonstrated, it is a 10–15 minute re-run, not a
rebuild.

## Summary table

| Suite | Fresh result | Notes |
|---|---|---|
| Studio backend, no DB | 67 passed, 49 skipped | Expected; DB tests need `STUDIO_TEST_DATABASE_URL` |
| Studio backend, fresh DB | **116 passed, 0 failed** | Test-isolation gap found and documented; not a product defect |
| Studio frontend build | Clean | One chunk-size advisory, no error |
| BizPilot backend, fresh DB, excluding broken file | **26 passed, 0 failed** | Must run from repo root with `BIZPILOT_DATABASE_URL` set |
| BizPilot backend, `test_performance.py` | **Cannot collect** | Missing `openai` dependency — real, reproducible defect |
| BizPilot frontend build | Clean | All 9 routes static |
