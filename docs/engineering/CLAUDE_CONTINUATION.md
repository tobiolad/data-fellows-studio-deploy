# Claude continuation notes — Studio AI execution runtime

This file exists so a future Claude session can continue this work without
repeating the full repository audit. Update it after each meaningful
increment.

## Current phase

Phase Two (shared AI execution platform) — Agent Registry + Model Gateway
— a cross-repo increment (BizPilot diagnostic-handoff receiver, Phase
Four's Studio side), a new referral-tracking capability, and the start of
Phase Six (a from-scratch frontend rebuild, owner-directed mid-session
after visual review of the existing portals). Phase Zero (takeover audit)
is done.

## Increment 3: frontend rebuild (React + Tailwind + shadcn/ui) + referral links

The owner reviewed screenshots of the existing `frontend/` (vanilla JS)
portals this session and asked for a full rebuild with a modern design
system — "every screen should scream excellence" — plus a referral-link
feature for onboarded accelerator/partner organizations.

**New frontend**: `frontend-next/` (Vite + React 19 + TypeScript + Tailwind
v4 + shadcn/ui's "Nova" preset, Radix-based). Deliberately a *separate* app
next to `frontend/`, not an in-place rewrite — `frontend/` keeps working
undisturbed until the owner decides to cut over. It talks to the exact same
backend API; no backend endpoint changed shape for the frontend's sake. See
`frontend-next/README.md` for what's real vs. `ComingSoonPage` placeholder.

Built this increment: sign-in (synthetic role picker, replacing the old
"Developer test controls" raw form), `AppShell` layout (dark-navy sidebar
matching the prior brand, indigo accent, role-aware nav), Admin overview,
Admin referral program page, Client overview, Professional overview, the
Reviewer submission queue (with approve/request-revision dialog wired to
`POST /api/deliverables/{id}/review`), and the flagship: a 5-step animated
profile-creation wizard (`src/pages/professional/ProfileWizard.tsx` —
react-hook-form + zod, `useFieldArray` for experience/education/portfolio/
evidence, framer-motion step transitions) that calls the existing
`PUT /api/professionals/{id}/profile` then `POST /api/professionals/{id}/application`
on submit. Verified by actually running it: seeded real data through the
live backend, drove it with Playwright, and visually confirmed every page
renders real data (screenshots were shown to the owner, not just described).

One real bug caught by doing this for real rather than describing it: the
Vite dev server's default port (5173) isn't arbitrary here — it's the exact
origin the backend's CORS `allow_origins` list already permits
(`backend/app.py`, alongside `127.0.0.1:5173`). Using a different port (8090
in an earlier manual check) silently fails every API call with a CORS error
and no visible app-level symptom beyond "Failed to fetch." If this ever
needs a different port, add it to that allowlist first.

**New backend capability — referral links** (not in the original master
handoff; added because the owner asked for it alongside the UI rebuild):
`migrations/013_referral_links.sql` (`referral_links`, `referral_events`).
`POST /api/referral-links` (admin) creates a link with a short public `code`
(shareable, e.g. `/r/<code>` records a visit) and a separate secret
`view_token` the partner can use to see their own link's visit/signup counts
at `GET /api/referral/<view_token>/stats` — no Studio account needed, by
design, since an external accelerator partner has no reason to have one.
`OrganizationCreate` gained an optional `referral_code`; creating an
organization with one records a 'signup' event (best-effort — an invalid
code doesn't fail organization creation). Organizations are still
admin-created only (no public self-serve signup exists in this system), so
"signup" here means an admin crediting a referral when onboarding a client
that came through a partner, not a public form. `backend/test_referral_links.py`
(5 tests). 63/63 backend tests pass (up from 58).

## Increment 2: BizPilot diagnostic-handoff receiver

See `docs/diagnostic-handoff.md` for the full contract. Summary: added
`POST /api/diagnostic-links` (admin-only, owner-authorized linkage of one
BizPilot engagement to one Studio organization) and
`POST /api/diagnostic-handoffs` (idempotent receiver, requires `admin` or
`diagnostics_service` role, creates an authorized engagement/project/work-
package shell from BizPilot's existing handoff payload, never auto-assigns
or runs AI). Migration `012_diagnostic_handoffs.sql`. New tests in
`backend/test_diagnostic_handoff.py` (5 tests, all passing). The matching
BizPilot-side change (wiring its existing but previously inert
`handoff/delivery` endpoint to actually call this receiver, opt-in via
`BIZPILOT_STUDIO_RECEIVER_URL`/`BIZPILOT_STUDIO_SERVICE_TOKEN`) is in
`bizpilot-pro-concept` PR #16.

This was verified across a real process boundary, not just with mocked
unit tests on each side: a live Studio `uvicorn` server actually received
an HTTP POST from BizPilot's real delivery code, carrying a handoff built
through BizPilot's genuine case/finding/recommendation/report workflow,
and the resulting Studio engagement/project/work-package were confirmed via
Studio's own read endpoints. See `docs/diagnostic-handoff.md`'s "Verified
end-to-end" section for exact commands if this needs reproducing.

## What was verified before any code was written

- The Studio repo's real state is a 54-deep stack of **open draft PRs**
  (`#1`–`#54`), none merged into `main` or the reported default branch
  `codex/studio-foundation`. The tip, branch `codex/studio-release-verification`
  (PR #54, commit `6435422`), contains the cumulative diff of the whole
  stack and is the actual, much-more-complete codebase — `codex/studio-foundation`
  is only the 3-commit bootstrap.
- This session's assigned branch, `claude/studio-ai-execution-handoff-8y0l2a`,
  was created pointing at that 3-commit bootstrap (a harness default, not prior
  Claude work — verified no unique commits existed on it). It was **reset onto
  `origin/codex/studio-release-verification`** so new work sits on the real,
  audited codebase instead of the stale bootstrap. The remote branch was
  force-pushed to match; nothing unique was discarded (confirmed via
  `git log` diff before resetting).
- PRs #3, #4, #5, #19 are explicitly flagged "Hold" in
  `docs/release/PR_INTEGRATION_AUDIT.md` — they conflict with the later
  PostgreSQL-based line and must stay held for owner-reviewed manual
  disposition, not merged.
- The actual codebase is much smaller than the handoff narrative implies: a
  single FastAPI backend (`backend/app.py`, ~1800 lines; `backend/persistence.py`,
  ~1400 lines after this increment), a static JS/HTML frontend with no SPA
  framework, 11 SQL migrations, and a `unittest`-based test suite (53 tests
  after this increment, all passing against real PostgreSQL 16 — see below).
- `docs/release/STAGING_RELEASE_REPORT.md`'s claim of 43 passing backend
  tests was independently reproduced (not just trusted) by actually running
  `python -m unittest discover -s backend -p 'test_*.py'` against a fresh
  local PostgreSQL 16 database. It matched exactly before this increment's
  changes.
- The AI execution surface before this increment was genuinely greenfield
  per the handoff's Phase Two description: `docs/ai-execution.md` and
  migration `002_ai_execution_controls.sql` described only a single
  hardcoded agent string (`"synthetic-planner-v1"`) inlined directly in the
  `create_ai_run` route handler, duplicated across the PostgreSQL and
  in-memory code paths. There was no agent registry, no model gateway, no
  provider adapter abstraction, and no per-agent budget enforcement. Grepping
  for `openai|anthropic|api_key|provider` in `backend/` returned no hits —
  confirming no real provider code exists anywhere in the repo.
- `backend/requirements.txt` pinned a nonexistent package, `httpx2` (no such
  PyPI package exists; it's a typo for `httpx`, which `fastapi.testclient`
  actually requires). This blocked `pip install` in a clean environment and
  has been fixed.

## What this increment implemented

1. **Migration `011_agent_registry.sql`** — new `ai_agents` table (name,
   purpose, capability category, provider, model, model version, allowed
   tools, data access scope, autonomy level, `requires_human_approval`,
   `budget_cap_cents`, owner, lifecycle status). Adds `agent_id`, `provider`,
   `model`, `model_version`, `input_tokens`, `output_tokens` columns to
   `ai_runs`. Seeds the existing deterministic executor as a fixed-UUID row
   (`00000000-0000-0000-0000-000000000001`, provider `synthetic`) so every
   prior caller that omits `agent_id` keeps resolving to the same agent the
   old hardcoded literal represented. Migrations 001–010 were **not**
   edited, per `docs/database-migrations.md`'s "never edit an applied
   migration" rule.
2. **`backend/model_gateway.py`** (new) — the single policy boundary between
   a run request and a provider. `resolve_adapter(provider)` returns
   `SyntheticPlannerAdapter` for `provider == "synthetic"` (deterministic,
   used by every test); any other provider is refused unless
   `STUDIO_AI_REAL_PROVIDER_APPROVED=1` is set, and even then no real adapter
   is registered — the flag only documents operator approval, it cannot by
   itself cause a real-model call. No provider credentials exist anywhere in
   this change.
3. **Agent registry API** — `POST /api/ai-agents` (admin only) and
   `GET /api/ai-agents` (admin or reviewer), backed by new
   `PostgresRepository.create_agent/list_agents/get_agent` methods. Registry
   endpoints require PostgreSQL persistence (`501` in memory mode, matching
   the existing pattern for not-yet-ported domains).
4. **`POST /api/ai-runs` now resolves a registry agent** instead of
   hardcoding output. It accepts an optional `agent_id` (defaults to the
   seeded synthetic agent), enforces that requested tools are a subset of
   the agent's `allowed_tools`, enforces that requested `budget_cents` does
   not exceed the agent's `budget_cap_cents`, calls
   `model_gateway.resolve_adapter(...).run(...)`, and persists
   `agent_id`/`provider`/`model`/`model_version` on the run. The independent
   reviewer-approval requirement for the resulting artifact is unchanged and
   is **not** affected by an agent's `requires_human_approval` flag — that
   flag is a recorded governance signal for future autonomy tiers, not a
   bypass. The in-memory (non-PostgreSQL) code path was deliberately left
   untouched to avoid any risk to its existing tests.
5. **Tests**: `backend/test_model_gateway.py` (pure unit tests, no DB) and
   `backend/test_agent_registry.py` (PostgreSQL integration tests, same
   `@unittest.skipUnless(STUDIO_TEST_DATABASE_URL)` pattern as the existing
   suite) covering: admin-only registration, reviewer/admin-only listing,
   default resolution to the seeded synthetic agent, per-agent budget cap
   enforcement, unknown-agent rejection, and refusal to execute against an
   unapproved real provider. `backend/test_persistence.py`'s hardcoded
   migration file list was updated to include `011_agent_registry.sql`.
6. Fixed the `httpx2` → `httpx` typo in `backend/requirements.txt`.
7. Extended `docs/ai-execution.md` with Agent Registry and Model Gateway
   sections.

## Tests performed (reproduced, not assumed)

```
sudo -u postgres psql -c "CREATE DATABASE studio_test;"
python3 -m venv <venv> && <venv>/bin/pip install -r backend/requirements.txt
export STUDIO_TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/studio_test
<venv>/bin/python -m unittest discover -s backend -p 'test_*.py'
```

Result after increment 1 (agent registry): **53 passed**. After increment 2
(diagnostic handoff): **58 passed**. After increment 3 (referral links):
**63 passed, 0 failed, 0 skipped** — all against a freshly created local
PostgreSQL 16 database each time (the suite is not safe to re-run against a
non-reset database — some tests accumulate state across runs; this is a
pre-existing property of the suite, not something any increment changed).

Also for increment 2: a real cross-repo smoke test (live `uvicorn` Studio
server + BizPilot's actual delivery code, no mocks) — see
`docs/diagnostic-handoff.md`. For increment 3: the new `frontend-next/` app
was run for real (`npm run dev`, backend seeded with real data) and driven
with Playwright to confirm every built page renders live data, not just
that it type-checks and builds.

Not run in this session: Playwright browser suite under `tests/playwright/`
(the *old* frontend's, now stale against the new one), container builds, CI
workflows themselves (inspected, not executed), Entra against a real
tenant, or anything involving Azure.

## Pending work (next recommended tasks, in dependency order)

0. **Frontend rebuild — essentially feature-complete for the backend that
   exists.** `frontend-next/` now covers every screen the sidebar links to
   except four, all wired to real backend data, no mocks: sign-in; Admin
   overview/referrals/applications+review-detail/engagements+membership/
   projects+work-packages+assignment/AI-operations (agent registry +
   register-agent dialog + run history with inline approve/reject); Client
   overview/deliverables/messages; Professional overview/profile-wizard/
   opportunities/assignments/deliverables/application-detail; Reviewer
   submission-queue and admission-review (the exact same components as
   Admin's, made role-aware via `basePath` computed from the session — no
   duplicate implementation).
   Still `ComingSoonPage` placeholder, and why: Admin Professional network
   (would substantially duplicate Applications & vetting filtered to
   `approved` — low enough value not to build a second screen for the same
   data) and Settings (no backing API, nothing concrete to wire up); Client
   Billing and Support (genuinely blocked on Phase Eight's Stripe
   integration and Phase Seven's support-ticket system, neither of which
   exist yet — building these would mean fabricating data, which the
   handoff explicitly forbids).
   Two real, narrow backend authorization gaps were found and fixed while
   building the Reviewer screens (not from reading the code — from actually
   clicking through the flow and hitting 403s): `GET
   /api/professionals/admissions` and `GET /api/professionals/{id}/application`
   were both missing the `reviewer` role even though a reviewer could
   already decide on any admission via `POST .../review`. Both now allow
   `admin` or `reviewer`, matching the authority reviewers already had.
   The old `frontend/` still works and is what's actually deployed by
   `ops/`/`Dockerfile`; cutting over (updating the container build, retiring
   `frontend/`) is an owner decision once the owner has reviewed
   `frontend-next/`, not something to do silently. Real Entra sign-in still
   needs to replace `frontend-next/src/pages/SignIn.tsx`'s synthetic picker,
   same gap the old frontend had.
1. **Branch integration plan for the owner.** The 54-deep PR stack needs an
   owner-approved merge sequence; this session did not merge anything. This
   increment's commits live only on `claude/studio-ai-execution-handoff-8y0l2a`
   (based on PR #54's tip) — they are not part of the stack and need their
   own draft PR against `codex/studio-release-verification` (or wherever the
   owner decides the stack should land).
2. **Task orchestration lifecycle.** Runs still complete synchronously
   (`queued`→`succeeded` with no real `running` state); the `ai_runs.status`
   CHECK constraint already allows `queued`/`running`, but nothing produces
   those states yet, and there's no cancellation-during-execution path since
   the synthetic adapter is instantaneous. This matters once any adapter is
   not instantaneous.
3. **Tool permission classification (section 7.4).** Only one tool
   (`planning`) exists anywhere in the system today, so the "subset of
   allowed tools" check added in this increment is structurally untestable
   beyond the trivial case. Adding a second tool type is the natural next
   step to exercise it for real.
4. **Budget/cost observability dashboard.** `spent_cents`/`input_tokens`/
   `output_tokens` are now plumbed through but always zero (synthetic
   adapter has no real cost). No operational dashboard reads them yet.
5. **AI Vetting v1 (Phase Three)** builds on `backend/admission.py` and the
   versioned evidence-attestation policy already in place (migration
   `008_professional_admission_review.sql`) — not started.
6. **Diagnostic-handoff read-back** (`Diagnostics.Summary.Read` /
   `Diagnostics.Handoff.Read` from BizPilot's contract) and a reviewer-facing
   screen showing which projects came from a diagnostic handoff — not
   started; see `docs/diagnostic-handoff.md`'s "Not yet implemented".
7. The documented project-completion gap (one accepted deliverable can
   satisfy a multi-package project) was confirmed to still exist and was
   **not** fixed in this increment — it's an existing-behavior change, not
   additive, and deserves its own reviewed slice.

## Known blockers

- No Azure work has been done or should be done yet, per explicit
  instruction.
- No real AI provider is configured or should be; `STUDIO_AI_REAL_PROVIDER_APPROVED`
  must stay unset outside an owner-approved, budgeted configuration change.
- The 54-PR stack's integration order is an owner decision, not something
  this session should resolve unilaterally.
