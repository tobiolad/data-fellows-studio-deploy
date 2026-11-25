# Architecture — verified, as actually deployed

This describes what is actually running, verified by direct inspection this
session, not the target architecture in the planning docs (which describe a
different, not-yet-built hosting plan — see `SYSTEM_AUDIT.md` §1).

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
