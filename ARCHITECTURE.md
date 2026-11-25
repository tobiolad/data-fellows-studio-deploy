# Architecture — verified, as actually deployed

This describes what is actually running, verified by direct inspection this
session, not the target architecture in the planning docs (which describe a
different, not-yet-built hosting plan — see `SYSTEM_AUDIT.md` §1).

## Three horizons (founder decision, 25 November 2026)

Three distinct things, not two, and they must not be conflated:

1. **Current live implementation**: Google OAuth, Vercel (frontend),
   Railway (backend + Postgres), a live Stripe restricted key. Verified
   this session (§"Studio: backend/frontend" below).
2. **Approved short-term operating arrangement**: the same stack as (1).
   The founder has explicitly authorized it as the operating environment
   for now — it is not a stopgap awaiting correction, it is the plan
   until (3) is funded and scheduled. Identity must be designed so a
   future provider (Entra or otherwise) can be added later without an
   auth rewrite (tracked in the durable-runtime phase below), but no
   migration is scheduled.
3. **Long-term target**: Azure, funded by the Microsoft for Startups
   scholarship (up to $150,000 in Azure credits) and Microsoft Foundry
   model access. Not scheduled; subject to its own cost/migration/
   security review before any infrastructure moves. The one near-term
   exception is evaluating the **Microsoft Foundry model API** as a
   controlled AI provider inside the existing model gateway — that does
   not require moving the Studio application itself, so it is in scope
   now while (2) continues to host everything else.

## Target logical architecture (AI + human workforce)

Founder-specified layering for the AI-native build. Each layer is a
separate component; nothing here ties the product to one model vendor,
SDK or cloud:

```
Client / Partner / Professional / Administrator
  -> Studio Applications and APIs                         [exists: backend/app.py, frontend-next/]
  -> Engagements, Projects, Work Packages, Assignments      [exists]
  -> AI and Human Work Orchestrator                        [does not exist yet]
  -> Durable Agent Task Queue and Workers                  [does not exist yet]
  -> Agent Registry + Agent Factory + Skills/Tool Registry  [registry exists (ai_agents); Factory and tool registry do not]
  -> Model Gateway                                          [exists: backend/model_gateway.py, synthetic-only]
  -> Microsoft Foundry DeepSeek / other approved providers  [does not exist; adapter to be built]
  -> Versioned Artifacts, Evaluations, Human Reviews        [artifacts/reviews exist; evaluations do not]
  -> Client Acceptance and Managed Support                  [exists]
```

What exists today, precisely (re-verified by reading the code this
session, not from memory):

- `ai_agents` (migration `011_agent_registry.sql`): one row per registered
  agent — name, purpose, capability_category, provider/model/model_version,
  allowed_tools (jsonb), data_access_scope, autonomy_level,
  requires_human_approval, budget_cap_cents, owner_actor_id, status
  (`active`/`disabled`). Only `POST /api/ai-agents` (create) and
  `GET /api/ai-agents` (list) exist — **no update, activate/disable, or
  retire route**. There is no lifecycle state machine (Draft → Testing →
  Awaiting Approval → Active → Suspended → Retired) at all; `status` is a
  flat two-value field set once at creation.
- `ai_runs` / `artifacts` (migration `001_initial.sql`, extended by `011`):
  a run is created and resolved to `succeeded` **synchronously, inside the
  HTTP request** (`create_ai_run` in `app.py`) — `status` has a
  `queued`/`running` state in its CHECK constraint that nothing ever
  produces, because the synthetic adapter is instantaneous. There is no
  queue, no worker process, no lease, no retry, no checkpoint.
- `model_gateway.py`: `resolve_adapter(provider)` is the one chokepoint
  every run goes through. The only adapter registered is
  `SyntheticPlannerAdapter`. Any other provider requires an operator to
  set `STUDIO_AI_REAL_PROVIDER_APPROVED=1`, which **only records that a
  human has reviewed and budgeted it** — no real adapter exists yet, so
  the flag alone cannot execute a real call. This is the correct seam for
  a Foundry adapter: add `FoundryAdapter(ModelAdapter)` here, nothing
  upstream changes.

This matches `REQUIREMENTS_TRACEABILITY.md` §5 exactly; nothing has
changed structurally since that audit except the registry's pre-existing
shape being confirmed suitable as the foundation for the Agent Factory
(Decision/mandate, 25 November) rather than needing a rewrite.

## Repositories

Three independent repositories, no shared package, no monorepo tooling:

- `Data-Fellows/data-fellows-studio` — the internal delivery platform (this
  document's subject).
- `Data-Fellows/bizpilot-pro-concept` — the client-facing diagnostic tool.
  Hands off a completed diagnostic to Studio over HTTP (`docs/diagnostic-handoff.md`
  in Studio documents the contract from the receiving side).
- `Data-Fellows/data-fellows-web-app` — the public marketing site
  (Next.js/Supabase). **Zero integration with Studio or BizPilot exists.**
  No shared auth, no shared data, no link between a marketing lead and a
  Studio organization. This is a real, open gap if marketing-to-delivery
  handoff is wanted (see `DECISIONS_AND_BLOCKERS.md`).

## Studio: backend

- **Runtime**: Python 3.12, FastAPI, served by Railway.
- **Database**: a single PostgreSQL instance on Railway. One schema, no
  read replica, no connection pooler beyond Postgres's own.
- **Persistence layer**: `backend/persistence.py` — one large class, every
  method takes the actor's id and enforces its own authorization (role,
  membership) before any query. There is no separate authorization
  middleware layer; the enforcement is colocated with each query. This is
  a deliberate pattern carried through the whole file (confirmed by
  reading every public method this session), not inconsistent per-method
  effort.
- **Migrations**: flat numbered SQL files in `migrations/`, applied in
  order by `persistence.py`'s own migration runner at startup, with a
  checksum guard against modifying an already-applied file. No separate
  migration tool (no Alembic, no raw `psql` scripting at deploy time).
- **External integrations**, each isolated to its own module:
  - `backend/stripe_billing.py` — Stripe Invoicing (built this session).
  - `backend/google_auth.py` — Google OAuth sign-in.
  - `backend/model_gateway.py` — AI provider abstraction (synthetic only
    today).
  - BizPilot handoff — received via a plain authenticated REST endpoint in
    `app.py`, not a separate module (small enough not to need one).
- **No background workers, no task queue.** Every request-handling path in
  the backend is synchronous within the request/response cycle. This is
  the single largest structural gap relative to the target architecture
  (see §5 of `REQUIREMENTS_TRACEABILITY.md`): any feature requiring a
  long-running or retryable background step (a real AI agent run, a
  scheduled digest, a retried webhook) has nowhere to live yet.

## Studio: frontend

- **`frontend-next/`** is the live frontend: React 19, TypeScript, Vite,
  Tailwind v4, shadcn/ui, TanStack Query for all server state, React
  Router for navigation, Sonner for toasts.
- **`frontend/`** (no `-next` suffix) is a legacy, superseded frontend.
  Confirmed by inspection this session: it is not built, not deployed, not
  referenced by any CI workflow or deploy config. It should be deleted or
  explicitly archived rather than left to confuse a future reader — flagged
  as a decision item, not actioned unilaterally.
- **Auth state**: `AuthProvider` (React Context) wraps the whole app;
  session is the backend's own HS256 JWT, stored client-side and attached
  by `lib/api.ts` to every request.
- **Role-based rendering**: `RequireAuth` now reads an "effective role"
  (real session role, overridden only for an admin's own client-side
  View-As preview) rather than the raw session role directly — the
  master prompt's instruction to never trust a frontend role check as an
  *authorization* boundary is upheld because every actual authorization
  decision (every write, every scoped read) is re-checked server-side in
  `persistence.py` regardless of what the frontend renders. The frontend
  role check governs only what is *shown*, never what is *allowed*.
- **Deployment**: Vercel, one project, auto-deployed from the repo's
  default branch (`codex/studio-foundation` — see `SYSTEM_AUDIT.md` §2 for
  why this, not `main`, is what's actually live).

## Request flow (typical authenticated action)

1. Browser → Vercel-hosted static frontend bundle.
2. Frontend → Railway-hosted FastAPI, bearer JWT in `Authorization` header.
3. FastAPI route handler (`backend/app.py`) parses/validates the request
   body with Pydantic, resolves the actor from the JWT, calls exactly one
   `persistence.py` method.
4. `persistence.py` method: opens a transaction, re-checks the actor's
   authorization for the specific object being touched (not just "is this
   role allowed to call this endpoint" — the row itself is checked, e.g.
   "is this actor a member of *this* organization"), performs the write,
   writes an `audit` row, commits.
5. Response flows back; TanStack Query caches and invalidates by query key.

For an external-system action (Stripe invoice send, Stripe webhook), the
same shape holds, with the external call made synchronously inside the
request and the result persisted before the response returns. There is no
retry or reconciliation loop beyond what the webhook itself provides.

## What does not exist yet, structurally

Carried forward from `REQUIREMENTS_TRACEABILITY.md` §5 for visibility at
the architecture level, since these are not features so much as missing
architectural layers:

- A job queue / background worker process.
- A file storage backend (no uploads exist anywhere in Studio).
- A caching layer (every read hits Postgres directly; fine at current
  scale, a decision point before any one is added for its own sake).
- A dedicated secrets manager (secrets live in Railway/Vercel environment
  variables).
- Any shared code path between Studio and BizPilot beyond the one HTTP
  handoff contract — they do not share a database, a session, or a
  deployment.
