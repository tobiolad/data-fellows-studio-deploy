# Requirements traceability — master build checklist, item by item

Statuses used: **Missing**, **Partially implemented**, **Implemented but
unverified**, **Verified locally**, **Verified in staging**, **Blocked**,
**Deferred with approval**. "Studio" means `Data-Fellows/data-fellows-studio`
unless stated. File references are relative to that repo unless prefixed
`bizpilot:`.

There is no staging environment distinct from production for Studio (see
`SYSTEM_AUDIT.md` §5), so "Verified in staging" is not currently reachable
for anything — items that would otherwise earn it are marked **Verified
locally** with a note, since what's actually running is production.

## §4 Core platform

| Requirement | Status | Files | Evidence | Next action |
|---|---|---|---|---|
| Secure auth and session management | Verified locally (production) | `backend/google_auth.py`, `backend/app.py` | HS256 Studio session JWT, 12h TTL; real Google sign-in and real admin use this session | Rotate `STUDIO_SESSION_SECRET` if ever exposed again (declined once already by founder) |
| Account invitation/onboarding/approval/revocation | Verified locally | `backend/persistence.py` (`upsert_google_account`, `set_account_role`), migration `014` | `test_accounts_api.py`; real production bootstrap of first admin done this session | Revocation of a *global role* (not just org membership) has no dedicated endpoint yet — only org membership can be revoked today |
| Server-side role/org authorization | Verified locally | `require_global`, `member`, every `persistence.py` method's own membership check | 116 tests include explicit cross-tenant-denial assertions | None open |
| Multi-tenant client isolation | Verified locally | Same as above + new admin-preview override, specifically tested for leakage | `test_admin_may_preview_a_specific_organizations_client_overview` asserts a real client cannot use the admin-only param | None open |
| Admin/client/professional/reviewer workspaces | Verified locally | `frontend-next/src/pages/{admin,client,professional,reviewer}/` | Every route has a real page; last placeholder (`/client/support`) replaced this session | Visual/UX excellence pass still open (§13) |
| Partner access limited to own info | Verified locally | `backend/app.py` referral-link endpoints | `test_referral_links.py` (5 tests) | None open |
| Private file storage, quarantine, malware scanning | **Missing** | — | No file upload exists anywhere in Studio; `project_documents` stores only metadata references | Real gap — no storage backend chosen, no scanning |
| Reliable Postgres migrations/transactions | Verified locally | `migrations/001`–`016`, `persistence.py`'s `transaction()` context manager | Checksum verification (`018` equiv.), replay rejection tested | None open |
| Versioned records and audit history | Verified locally | `audit` table, `_audit()` helper on every write | Read via `/api/audit`, scoped per-org | None open |
| Notifications, conversations, project requests | Verified locally | `notifications`, `project_messages`, `project_requests` tables; **this session added the first admin UI for requests** (was backend-only before) | Full round-trip proven live via Playwright this session | None open |
| Search, filters, pagination, reporting | Partially implemented | `GET /api/professionals/admissions?status_filter=`, `/support-requests?status_filter=`, reviewer-queue pagination (`offset`) | Filtering exists per-list; no cross-entity search, no saved reports | Low priority until a real reporting need appears |
| Safe error handling/recovery | Partially implemented | HTTPException details are founder-readable sentences throughout; no structured incident/runbook for an unhandled 500 in production | No crash seen yet in production | Add a basic error-monitoring hook (§18 asks for this too) |

## §5 Shared AI workforce engine

| Requirement | Status | Files | Evidence | Next action |
|---|---|---|---|---|
| Agent registry, versioned config | Verified locally | migration `011_agent_registry.sql`, `backend/app.py` agent endpoints | `test_agent_registry.py` | None open |
| Named human owner per agent | Verified locally | `ai_agents.owner_actor_id`, enforced at creation | Same | None open |
| Capabilities/autonomy policy | Partially implemented | `capability_category`, `autonomy_level`, `requires_human_approval` columns exist and are recorded | Not yet enforced as a graduated policy (no Level 0–4 distinction from the AI Workforce Strategy doc is implemented — it's a flat flag today) | Map the doc's 5 autonomy levels onto the existing columns, or add one |
| Provider-independent model gateway | Verified locally | `backend/model_gateway.py` | `test_model_gateway.py`; refuses any non-`synthetic` provider unless an unset env flag is present | None open |
| Approved provider/model config | Deferred with approval | Same file | No real provider registered; `STUDIO_AI_REAL_PROVIDER_APPROVED` intentionally unset | Needs a founder-approved provider, budget and policy before any real call |
| Durable task queue, background workers | **Missing** | — | `ai_runs` completes synchronously inline in the request; no queue, no worker process | Real gap for anything beyond instantaneous synthetic execution |
| Persistent execution state/checkpoints | Partially implemented | `ai_runs.status` CHECK allows `queued`/`running` | Nothing ever produces those states — synthetic adapter is instantaneous | Needs a real (even if still synthetic-but-slow) adapter to exercise |
| Task dependencies/scheduling | **Missing** | — | No concept of one AI run depending on another | Not started |
| Pause/resume/cancel/retry/timeout | Partially implemented | `POST /api/ai-runs/{id}/cancel` exists | Cancellation of an instantaneous synthetic run is not meaningfully testable yet | Same blocker as above |
| Human intervention/escalation | Partially implemented | Independent reviewer approval on the resulting artifact is real and enforced | No mid-run escalation path (nothing runs long enough to need one) | — |
| Agent-to-agent handoffs | **Missing** | — | Only one tool (`planning`) and one agent type exist | Needs a second real capability to exercise |
| Agent-to-human / human-to-agent handoffs | Partially implemented | Reviewer approval is the human-to-agent-output boundary | No agent ever asks a human a question mid-task | — |
| Tool registry, per-action authorization | Partially implemented | `allowed_tools` on each agent, checked as a subset at run creation | Only one tool exists, so the check is real but structurally untested beyond the trivial case (documented limitation, carried from `CLAUDE_CONTINUATION.md`) | Add a second tool type |
| Isolated code execution, restricted network | **Missing** | — | No agent runs arbitrary code at all yet | Not applicable until one does |
| Structured input/output validation | Verified locally | `validate_synthetic_output()` in `app.py` | Rejects a malformed synthetic artifact | None open |
| Versioned artifacts and evidence | Verified locally | `artifacts` table, linked to `ai_runs` | — | None open |
| Tenant-scoped knowledge retrieval | **Missing** | — | No retrieval/RAG exists | Not started |
| Prompt/skill/model version tracking | Verified locally | `agent_version`, `policy_version`, `model_version` columns | — | None open |
| Token usage, real costs, budget enforcement | Partially implemented | `budget_cents`/`spent_cents`/`input_tokens`/`output_tokens` plumbed through; always zero (synthetic has no real cost) | No real-cost data exists anywhere | Moot until a real provider is approved |
| Evaluation datasets, regression tests | Partially implemented | Unit tests exist for the gateway and registry; no formal eval dataset | — | Build alongside the second real agent |
| Agent activity history, monitoring | Partially implemented | `ai_runs`/`audit` give history; no dashboard | — | §18 asks for basic monitoring generally |
| Emergency stop, disablement | Verified locally | Agent `status` can be set `disabled`; `model_gateway` refuses non-approved providers outright | — | None open |

**Overall**: the registry/gateway/registry-to-run path is real and tested;
everything downstream of "the synthetic adapter runs instantly" is
structurally unbuilt because nothing has needed it yet. This matches
`docs/engineering/CLAUDE_CONTINUATION.md`'s own "pending work" list exactly —
nothing has changed here since 24 November.

## §6 Human + AI collaborative workspace

| Requirement | Status | Files | Evidence |
|---|---|---|---|
| Shared task timeline | Partially implemented | `audit` + work-package/deliverable status | No single unified timeline view, but the data exists |
| Agent execution progress/status | Partially implemented | `ai_runs.status` | Only `queued`/`succeeded`/`failed` actually occur |
| Human assignment/ownership | Verified locally | `assignments` table, full accept/decline lifecycle | `test_app.py`, `test_persistence_api.py` |
| Task comments/instructions | Verified locally | `project_messages` | Full round-trip; admin UI added this session for the *request* variant |
| Requests for specialist assistance | **Missing** | — | No "pull in another professional" flow exists |
| Human takeover of agent work | **Missing** | — | No agent task has ever needed a human takeover path yet |
| Human corrections, return to agent | **Missing** | — | Same reason |
| Version comparison, artifact history | Verified locally | `deliverables.version`, immutable per version | `test_app.py` revision tests |
| Approval requests with evidence | Verified locally | Reviewer review + client acceptance, both evidence-linked | — |
| Reviewer work queues | Verified locally | `GET /api/reviewer/queue` | Requires the reviewer's own org membership — documented, not a bug (`SYSTEM_AUDIT.md` doesn't flag it as one either) |
| Rejection, revision, resubmission | Verified locally | `request_client_revision`, version increment on resubmit | `test_app.py` |
| Client acceptance of exact version | Verified locally | `accept_deliverable` binds to one `deliverable_id` | — |
| Project-level cost/progress tracking | **Missing** | — | No budget concept exists at the project level (only at the AI-run and, as of this session, invoice level) |

**Known defect named explicitly in the master prompt**: "Fix the known
multi-work-package completion defect." **Status: confirmed still present,
not fixed.** `docs/engineering/CLAUDE_CONTINUATION.md` recorded this on 24
November ("one accepted deliverable can satisfy a multi-package project...
not fixed in this increment"); I independently re-read `project_complete`
in `persistence.py` for this audit and confirm the completion rule still
checks for *any* accepted deliverable, not *all required* work packages.
This is Studio task #15 and remains the single most important open
correctness gap in the delivery lifecycle. See `DECISIONS_AND_BLOCKERS.md`.

## §7 Professional workforce

| Requirement | Status | Evidence |
|---|---|---|
| Application / invitation | Verified locally | Google-authenticated signup → admin-assigned role → self-submitted application, full chain proven this session |
| Profile, skills, evidence | Verified locally | `ProfileWizard.tsx`, `professional_profiles` table, versioned |
| AI-assisted screening | **Missing** | No AI touches an application yet (Phase Three, not started) |
| Role-specific assessments | **Missing** | Same |
| Practical exercises, rubrics | **Missing** | Same |
| Credential verification | Partially implemented | Evidence references have a `verified`/`unverified` status field; verification is manual, by a reviewer, not automated |
| AI-supported assessment reports | **Missing** | — |
| Independent human admission decision | Verified locally | `review_professional_admission`, self-review explicitly blocked | 
| Clarification/reconsideration requests | Partially implemented | `assessment` status + `missing_information` field exist; no dedicated "ask for reconsideration" UI |
| Approved directory | Verified locally | `/admin/professionals` (built this session) |
| Skills/availability matching | **Missing** | Opportunities are posted and browsed; no automated matching |
| Opportunities, assignment acceptance | Verified locally | `opportunity_interests`, `assignments` |
| Scoped project access | Verified locally | Same authorization pattern as everywhere else |
| Performance/quality records | **Missing** | No aggregate performance record beyond individual deliverable reviews |
| Compensation records/approval | **Missing** | No professional-payout concept exists (client billing shipped this session; professional compensation did not) |
| Suspension/revocation/offboarding | Verified locally | Membership revocation; admission can be set to `revoked` | 

## §8 Client delivery lifecycle

| Stage | Status | Notes |
|---|---|---|
| HubSpot company/deal mapping | **Missing** | No HubSpot integration exists in Studio at all |
| Client onboarding/org setup | Verified locally | Admin-created organizations + membership |
| Discovery/requirements intake | **Missing** | No structured intake form; handled outside Studio today |
| Reviewed BizPilot diagnostic handoff | Verified locally (cross-repo) | `docs/diagnostic-handoff.md` — proven across a real process boundary this session (live BizPilot → live Studio, no mocks) |
| Proposal/SOW management | **Missing** | Not in Studio |
| Scope/milestones/budgets/acceptance criteria | Partially implemented | Work packages carry acceptance criteria; no milestone or budget concept |
| Authorized agreement → project creation | **Missing** | Project creation is a direct admin action with no agreement record behind it |
| AI-assisted project planning | **Missing** | Work packages are created manually |
| Task/dependency management | Verified locally | `work_packages.depends_on` |
| Human + AI workforce allocation | Partially implemented | Human allocation is real; AI allocation to a *delivery* task doesn't exist (AI runs are a separate, parallel concept, not yet attached to a work package's actual delivery) |
| Deliverable submission/evidence | Verified locally | — |
| Independent quality review | Verified locally | — |
| Client revision/acceptance | Verified locally | — |
| Change requests/scope approval | **Missing** | `project_requests` is a general-purpose request, not a scope-change-specific flow |
| Handover documentation | Verified locally | `project_handovers`, accepted-version manifest, frozen at completion |
| Completion rules | **Blocked — known defect** | See §6 above |
| Ongoing managed support | Verified locally (this session) | `support_requests`, built and shipped this session; no SLA/severity tracking yet |

## §9 BizPilot integration

See `SYSTEM_AUDIT.md` §4 for fresh test evidence (26/26 passing, one
unrelated test file broken by a missing dependency). Checklist:

| Requirement | Status |
|---|---|
| Diagnostic case creation | Verified locally (bizpilot) |
| Authorized evidence collection | Verified locally |
| Data quality/validation | Verified locally (`test_diagnostics.py` covers file validation) |
| Workflow analysis | Verified locally |
| Findings linked to evidence | Verified locally |
| Recommendations/prioritization | Verified locally |
| Risks/assumptions/impact | Partially implemented — present in report rendering, not independently verified this audit |
| Human review of diagnostic reports | Verified locally |
| Secure versioned handoff to Studio | Verified locally — cross-repo, real process boundary, this session |
| Org mapping/authorization | Verified locally |
| Duplicate handoff prevention | Verified locally (idempotent receiver, `docs/diagnostic-handoff.md`) |
| **Handoff read-back and status** | **Missing** — `Diagnostics.Summary.Read`/`Diagnostics.Handoff.Read` from the contract are not implemented on the Studio side (Studio task #14, unchanged since 24 Nov) |
| Traceability findings → requirements | Partially implemented — the handoff creates a project shell; nothing traces an individual finding to an individual work package |

## §10 AI departments

**Status: one useful task proven end-to-end (planning), eight departments
not started.** This matches the master prompt's own instruction ("prove the
entire lifecycle before expanding... do not create nine empty agent
profiles") — Studio has exactly one real agent type wired through the
registry → gateway → run → artifact → reviewer-approval path, synthetic
only. No commercial research, BizPilot, vetting, engineering, data,
QA, ops or product-research agent exists as a distinct registered agent yet.
This is the correct state per the master prompt's own sequencing, not a gap
to rush.

## §11 Commercial operations and partner management

| Requirement | Status | Notes |
|---|---|---|
| Service offers/engagement types | **Missing** | — |
| Proposals/contracts/payment schedules | **Missing** | — |
| Project budgets/expenses | **Missing** | — |
| Human delivery costs | **Missing** | — |
| AI execution costs | Partially implemented | Plumbed, always zero (§5) |
| Professional compensation records | **Missing** | — |
| **Stripe test-mode integration** | **Implemented, but live-mode, not test-mode** — see `SYSTEM_AUDIT.md` §1. A real `rk_live_` key is configured and has been used for a real customer and a real sent invoice. | Founder-approved, done knowingly; flagged because the checklist literally asks for test-mode |
| Signed webhook validation | Verified locally (and live) | `backend/stripe_billing.py::verify_webhook_signature`, HMAC-SHA256, 5-minute replay window; proven against a real Stripe webhook this session |
| Idempotent payment processing | Verified locally (and live) | `stripe_webhook_events` dedup table; `record_webhook_event` returns `False` on redelivery; tested and proven live |
| Payment reconciliation | Partially implemented | Webhook updates local invoice status from Stripe's own report; no broader reconciliation job (e.g. "list all open invoices, re-poll Stripe") exists yet |
| Invoices and billing history | Verified locally (and live) | `/client/billing`, `/admin` org invoice section, both built and proven this session |
| Project gross margin/profitability | **Missing** | — |
| Partner organization management | Verified locally | Referral links |
| Referral links/attribution | Verified locally | `test_referral_links.py` |
| Partner-specific reporting | Partially implemented | View-token stats endpoint exists; no dashboard |
| Referral abuse prevention/privacy | Partially implemented | Secret view-token design prevents casual abuse; no rate limiting |

## §12 Managed support and continuous improvement

| Requirement | Status |
|---|---|
| Client support requests | Verified locally (this session) |
| Support tickets, severity | Partially implemented — a request is `open`/`resolved` only, no severity field |
| Incident history/escalation | **Missing** |
| SLA tracking | **Missing** |
| System health monitoring | **Missing** |
| AI-assisted incident investigation | **Missing** |
| Human-approved remediation | **Missing** |
| Controlled low-risk automation | **Missing** |
| Recovery/rollback | Partially implemented — Railway/Vercel both support redeploy-to-previous; not exercised as a drill |
| Post-incident reviews | **Missing** |
| Reusable workflows / knowledge base | **Missing** |
| Reusable integration components | **Missing** |
| Agent skill/eval improvements | **Missing** |

## §13 Every screen excellent

**Functional completeness: verified locally.** Every role (admin, client,
professional, reviewer) has a real screen behind every nav link; the last
placeholder (`/client/support`) was replaced this session, and a genuine
UX gap (admins had no screen to decide a client's project request) was
found and fixed. See `SCREEN_REFERENCE_LIBRARY.md`, `SCREEN_BY_SCREEN_IMPLEMENTATION.md`
and `PRODUCT_UX_AUDIT.md` in `docs/`/`docs/quality/` for the prior detailed
pass.

**Design excellence, accessibility, responsive/keyboard pass: not
re-verified by this audit.** `docs/quality/STUDIO_DESIGN_SYSTEM.md` and the
185-combination responsive/accessibility gate referenced in
`STAGING_RELEASE_REPORT.md` predate the frontend rebuild (`frontend-next/`)
and the three features added this session (billing, support, admin
view-as). This is real, open work — Studio tasks #8–#11 — not started in
this session because the founder's own instruction was "prioritize
everything working first."

## §14 Security, privacy, reliability

Covered in depth in `SECURITY_THREAT_MODEL.md`. Headline items only here:

| Requirement | Status |
|---|---|
| Tenant isolation, object-level authorization | Verified locally |
| Least-privilege service identities | Partially implemented — Railway/Vercel deploy keys are scoped to their own services; no formal least-privilege review done |
| Secure auth, account linking | Verified locally |
| Secret management | Partially implemented — secrets live in Railway/Vercel env vars, not in a dedicated secrets manager; `STUDIO_SESSION_SECRET` was once pasted in chat and the founder declined rotation |
| Input validation / injection prevention | Verified locally — Pydantic models throughout, parameterized SQL everywhere in `persistence.py` |
| Rate limits / abuse protection | **Missing** — no rate limiting exists anywhere in the API |
| Prompt-injection defenses | Partially implemented — `validate_synthetic_output` rejects malformed output; nothing tests prompt injection because no real model is wired in yet |
| Agent tool misuse prevention | Verified locally for the one tool that exists (`allowed_tools` subset check) |
| File upload validation/quarantine | **Missing** (no uploads exist) |
| Dependency/vulnerability scanning | **Missing** — no Dependabot/Snyk-equivalent configured that I could find |
| Supply-chain checks | **Missing** |
| Audit log integrity | Verified locally — Postgres append-only `audit` table, no update/delete path in code |
| Data retention/deletion | **Missing** — no retention policy implemented anywhere |
| Sensitive-data redaction in logs | Partially implemented — health/ready endpoints explicitly avoid leaking DB details; general app logging not audited |
| Encryption in transit/at rest | Verified locally for transit (HTTPS everywhere via Vercel/Railway); at-rest encryption is whatever Railway's managed Postgres provides by default, not independently confirmed |
| Backup/restore testing | **Missing** — not attempted |
| Transaction/concurrency testing | Partially implemented — `FOR SHARE`/`FOR UPDATE` row locks used in several persistence methods; no dedicated concurrency test suite |
| Idempotent external actions | Verified locally — Stripe webhook dedup, diagnostic-handoff dedup both tested |
| Recovery from worker/provider failures | **Missing** — no worker exists yet to fail |
| Documented incident response | Partially implemented — `docs/security/session-revocation.md`-equivalent exists for token exposure; nothing broader |

## §15 End-to-end acceptance tests A–O

| Journey | Status |
|---|---|
| A. Professional applies → assessed → approved → accepts assignment | Verified locally (this audit's own golden-path run, §4 of `TEST_EVIDENCE.md`) — minus the AI-assessment step, which doesn't exist yet |
| B. Client onboarded from commercial opportunity, reviewed BizPilot diagnostic | Partially verified — the BizPilot→Studio handoff is proven; "onboarded from a commercial opportunity" (HubSpot) is not, since no HubSpot link exists |
| C. Engagement → project → dependent work packages | Verified locally |
| D. Agent runs, uses tools, produces artifact, records cost | Verified locally (synthetic; cost always zero) |
| E. Agent requests human help, resumes | **Missing** — no such path exists |
| F. Reviewer rejects, workforce revises, reviewer approves correct version | Verified locally |
| G. Client requests changes, accepts | Verified locally |
| H. Project completes only when all required work/approvals satisfied | **Blocked — known defect**, see §6 |
| I. Stripe test events reconciled, billing updated | Verified locally **and live** — but live-mode, not test-mode (see §11) |
| J. Support ticket → agent investigates → human authorizes resolution | Partially verified — the ticket and human-resolves path is real (this session); no agent investigation exists |
| K. Partner refers, sees only authorized stats | Verified locally |
| L. Unauthorized cross-tenant access denied | Verified locally |
| M. Worker crash mid-execution, safe resume, no duplicate external action | **Missing** — no worker exists to crash |
| N. Task exceeds budget, stops safely | Verified locally (budget-cap-exceeded rejection at run creation) — not tested mid-execution, since nothing runs long enough |
| O. Backup restored, critical workflows pass | **Missing** — not attempted |
