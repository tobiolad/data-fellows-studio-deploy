# Master build checklist — phase-ordered

Restructured 25 November 2026 to follow the founder's phase sequence
(§16 of "Founder Response to System Audit & Full AI Workforce Build
Mandate"). Supersedes the earlier P0–P4 priority list, which is folded in
below where it maps directly. Each item names the file(s) it touches and
its dependency on earlier items.

## Phase 0 — Stabilize what exists

Nothing here is new scope; all of it is either an already-approved fix or
already-identified risk. No item in Phase 1+ starts before this phase's
code items are merged (on the dev branch) and its security items have an
executed, confirmed rotation.

1. **Project completion defect** (Decision 5, approved). Fix
   `project_complete` in `persistence.py` so a project with several
   required work packages completes only when every required one is
   accepted, not on the first. Test: multi-package, a rejected package,
   an optional package, and a revision mid-flight. Run the full backend
   suite fresh before proposing.
2. **BizPilot `openai` dependency** (Decision 6, approved). First
   determine whether `async_ai_service.py` is active, optional, or dead
   code (check whether any live route or scheduled job imports it
   transitively). Fix the packaging problem without adding a paid
   provider dependency unless the module is actually active and needed.
   Run BizPilot's suite fresh after.
3. **Test-isolation hygiene** (found this session, `TEST_EVIDENCE.md`).
   The integration suite gives false failures when run twice against a
   database that isn't truncated between runs. Add a `setUp`/fixture that
   truncates the relevant tables (or documents the "always use a fresh
   database" requirement loudly enough in `README.md`) so this doesn't
   cost someone an afternoon again.
4. **Stripe key rotation** (Decision 2, approved, controlled). Write the
   rotation plan first (new restricted key's exact permissions, which
   env vars/integrations reference it, rollback step, what to watch
   after cutover), get it confirmed, then execute. No key value in chat,
   docs, logs or commits at any point.
5. **`STUDIO_SESSION_SECRET` rotation** (Decision 3, approved, security
   priority). Same shape: plan (new secret generation method, how every
   signed session gets invalidated, what users will see, who's affected),
   confirm, execute.
6. **$1 verification invoice** — inspect and report (Decision 4); act
   only once its actual status is known.
7. **PR reconciliation report** (Decision 7). Diff each of Studio's 38
   open PRs and BizPilot's queue against the canonical branch and the
   live deployed commit; classify each as already-merged content,
   still-useful, or conflicting. No merges from this; it's an input to a
   later founder decision.
8. **Controlled release process** (new blocker A in
   `DECISIONS_AND_BLOCKERS.md`). Design, propose, and — once confirmed —
   execute the first deliberate release from `Data-Fellows/data-fellows-studio`
   to the `tobiolad/data-fellows-studio-deploy` mirror Vercel/Railway
   actually build from. Every release after this one follows the same
   named step; nobody pushes to the mirror ad hoc again.

## Phase 1 — Durable execution

Depends on: Phase 0 code items merged (so the schema/tests they touch
aren't also mid-flight here).

- Persistent task and execution-attempt records, worker claiming with
  leases, task dependencies, retries with exponential backoff,
  idempotency for external actions, timeouts/cancellation, pause/resume,
  human-intervention checkpoints, budget checks before model/tool calls,
  crash recovery, versioned outputs, audit events, failed-task
  inspection, safe shutdown.
- State machine: `Created → Queued → Running → Awaiting Human Input →
  Resuming → Awaiting Review → Approved`, plus `Failed`, `Cancelled`,
  `Rejected`.
- Evaluate first whether a Postgres-backed queue (a table with
  `SELECT ... FOR UPDATE SKIP LOCKED`-style claiming, same database
  Studio already runs) is sufficient at current scale before reaching
  for a message broker — the founder's own instruction is not to add
  infrastructure the current workload doesn't need.
- Every resumed task re-validates permissions and policy at resume time;
  an earlier approval never carries indefinite privilege.
- Proven entirely with synthetic execution before Phase 3 touches it.

## Phase 2 — Agent Factory and tools

Depends on: Phase 1 (an agent's lifecycle transitions need somewhere
durable to record against) and the existing registry (preserved, not
rewritten).

- Extend `ai_agents` with lifecycle status (`draft`, `testing`,
  `awaiting_approval`, `active`, `suspended`, `retired`) replacing the
  current flat `active`/`disabled`, plus the fields the mandate lists
  (system instructions, reusable skills, cost/execution limits,
  evaluation requirements) that don't already exist on the row.
  Migration only where the current schema truly can't support it.
- Agent Factory admin workspace: create from template, configure job and
  model, attach skills/tools, assign a human supervisor, set
  permissions/spending limits, run synthetic evaluations, compare
  versions, submit for approval, activate/disable/retire, inspect
  history.
- Hard rule, enforced server-side: an agent can never approve its own
  activation, raise its own permissions, or raise its own spending
  limit. A new privileged tool or execution capability still requires an
  engineering-reviewed deployment, never a Factory-only configuration
  change.
- Tool Gateway: each tool declares input/output schema, required
  permission, execution environment, timeout, data classification,
  audit fields, and whether human approval is required. Every call goes
  through server-side authorization; raw model output never becomes an
  unrestricted shell command, SQL mutation, network request or
  deployment action. Prompt-injection, cross-tenant-access and
  tool-misuse tests from the first tool onward, not added later.

## Phase 3 — Microsoft DeepSeek integration

Depends on: Phase 2's model-gateway seam (adding one adapter, nothing
upstream changes) and the founder answering blocker B (scholarship
balance, expiry, which deployment, billing owner, terms).

- Verify the 8 facts the mandate lists (§5) before writing any adapter
  code.
- Build `FoundryAdapter(ModelAdapter)` in `model_gateway.py`: server-side
  auth, model/deployment selection, structured messages/outputs, tool-
  calling support (verified per model, not assumed), timeouts/
  cancellation, rate-limit handling, safe retries, token usage and
  measured cost, error classification, provider health, model-version
  tracking, privacy/data-processing controls.
- Keep synthetic execution as the default until the deployment, billing
  and data safeguards are verified; flip one agent to the real adapter
  only after that and after explicit approval.
- Design (not activate) Anthropic/OpenAI adapter interfaces for the
  future. Claude Pro remains a development tool, never the workforce's
  production API.

## Phase 4 — AI and human collaboration

Depends on: Phase 1 (checkpoints/intervention states) and Phase 2
(agents that can actually request help).

- Shared task ownership, execution timeline, agent progress/tool
  activity, a human instruction/feedback panel, specialist-assistance
  requests, human takeover, agent continuation after intervention,
  artifact versions/comparison, reviewer queues, escalation
  notifications, client-visible approved deliverables only.
- The founder's own worked example (data-engineering agent pauses for a
  business-rule clarification, resumes from checkpoint, QA checks it,
  independent human approves, only the approved version reaches the
  client) is the acceptance scenario for this phase, not a hypothetical.

## Phase 5 — Operational AI roles

Depends on: Phases 2–4. Exactly five agents, each a real capability, not
a prompt with a department name:

1. **Project Planning Agent** — proposes work packages, dependencies,
   acceptance criteria, risks from approved requirements; human delivery
   lead approves.
2. **Engineering Agent** — works authorized software/SQL/integration/
   transformation tasks in an isolated environment; produces versioned
   code, tests, docs; cannot deploy to production itself.
3. **Quality Assurance Agent** — reviews engineering output against
   acceptance criteria, runs checks, prepares evidence; never substitutes
   for required independent human approval.
4. **BizPilot Business Analyst Agent** — investigates a diagnostic case
   from authorized evidence, drafts findings/recommendations; human
   analyst reviews before any Studio handoff.
5. **Professional Assessment Agent** — assists screening/practical
   assessment/evaluation summaries; never makes the admission decision
   itself.

## Phase 6 — Commercial integration

Depends on: Phase 5 producing real work to attach costs and outcomes to.

- Connect the workforce to approved client projects, cost accounting
  (provider/model/agent/task/organization/project/work-package/
  department/billing-period), approved budgets at company/project/
  agent/task level with a hard stop on exhaustion (never relying on
  Azure budget alerts alone), a global emergency AI shutdown switch, and
  the AI Operations admin surface (§13 of the mandate).
- Measure scholarship consumption against its finite balance; have a
  realistic plan for when it ends.

## Phase 7 — Product quality and release

- Usability, security, concurrency, performance and end-to-end
  verification across everything built above.
- Update the release plan to reflect the current production environment
  (Decision 1/10) while preserving the Azure option, not re-introducing
  Azure/Entra as a near-term requirement.

## Definition of done (binding on every phase above)

An agent is not operational because it exists in the registry. It is
operational when it can receive an authorized task, access only
permitted tools/context, perform real work, persist its output, account
for its cost, request human help when it needs to, survive a failure,
and submit for the review its policy requires. A workflow is complete
only when an authorized user can run it end to end through Studio with
real persisted records and reproducible tests. Anything still running
against the synthetic adapter is labeled as such, everywhere it's shown.
