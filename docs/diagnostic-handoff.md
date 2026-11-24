# BizPilot diagnostic handoff receiver

Studio's half of the contract documented in BizPilot's
`docs/architecture/studio-integration.md`. Two deliberately separate steps,
matching that contract's two `Diagnostics.Link.Write` operations:

## 1. Link (owner-authorized, happens once per BizPilot engagement)

`POST /api/diagnostic-links` (admin only) connects one external BizPilot
engagement id to one existing Studio organization:

```json
{"organization_id": "<studio org uuid>", "source_engagement_id": "<bizpilot engagement uuid>"}
```

This never happens automatically from a handoff payload. Data Fellows owns
the client relationship and the organization mapping; a handoff cannot
create or choose an organization. Unique on `(source_system,
source_engagement_id)` -- a second link attempt for the same engagement is
rejected (`409`), not silently reassigned.

## 2. Handoff (idempotent, called by the BizPilot service identity)

`POST /api/diagnostic-handoffs` requires the `admin` or `diagnostics_service`
role (the latter is the production shape: an Entra workload identity with a
service app role, not a user). It accepts BizPilot's existing handoff
payload shape (`schema_version`, `engagement_id`, `report_id`,
`report_version`, `problem`, `desired_outcome`, `work_packages[]`) plus the
`idempotency_key` BizPilot already generates per delivery attempt.

Processing, inside the already-linked organization:

- Looks up the link by `engagement_id`; `404` if none exists -- a handoff
  for an unlinked engagement is refused, not queued.
- Idempotent on `(link, idempotency_key)`: a repeated delivery (BizPilot's
  own retry behavior) returns the exact same engagement/project/work-package
  ids instead of duplicating them.
- Creates one Engagement (`authorized`), one Project, and one Work Package
  per approved recommendation (`unassigned`, `acceptance_criteria` from the
  recommendation's `acceptance` text) -- using the linking admin's `owner`
  membership, so the existing `_require_owner` authorization on
  `create_engagement`/`create_project`/`create_work_package` is unchanged,
  not bypassed.
- Records sanitized evidence references (citation id/provider/url/mode --
  never raw datasets, per the contract's explicit exclusion) per work
  package in `diagnostic_handoff_work_packages`.
- **Never** auto-assigns a professional and **never** starts an AI run.
  The handoff creates the authorized shell; a human member of the Studio
  team plans and staffs it through the existing assignment and AI-run
  workflows exactly as for any other project.

Schema: migration `012_diagnostic_handoffs.sql` (`diagnostic_links`,
`diagnostic_handoffs`, `diagnostic_handoff_work_packages`).

## Verified end-to-end, not just unit-tested

Beyond the PostgreSQL-backed `backend/test_diagnostic_handoff.py` suite, this
was exercised across a real process boundary: a live Studio server (`uvicorn`,
`STUDIO_PERSISTENCE=postgres`) received an actual HTTP POST from BizPilot's
own `backend/diagnostics/reports.py` delivery code (its `studio_client`
module configured to point at that live server), carrying a handoff built
through BizPilot's real case -> finding -> recommendation -> report ->
handoff workflow. The resulting engagement/project/work package were then
independently confirmed to exist via Studio's own read endpoints. No part of
this path was mocked. It was not repeated on every CI run -- it is a
one-time manual verification of this increment, recorded here rather than
claimed from a mocked test.

## Not yet implemented

- `Diagnostics.Summary.Read` / `Diagnostics.Handoff.Read` (read-back
  operations from BizPilot's contract) -- Studio has no corresponding
  endpoint yet.
- Real Entra workload-identity validation for the `diagnostics_service`
  role -- today it is exercised only via the test-mode synthetic bearer
  token (`test:<actor>:diagnostics_service`), identically to every other
  role in this codebase.
- A reviewer-facing surface that shows which projects originated from a
  diagnostic handoff (the provenance is persisted and queryable, but no
  portal screen reads it yet).
