# Google sign-in

An alternative to Microsoft Entra: anyone can sign in with Google, but
Studio — not Google — decides what they can do once they're in.

## Why Studio owns accounts, not Entra

Entra's authorization model (`backend/auth.py`) reads a workspace role
straight off the token: an Entra admin assigns exactly one Studio app role
(`admin`/`reviewer`/`professional`/`client`) to a person outside Studio
entirely. Google has no equivalent concept — it only ever proves "this is a
real, verified email address." So Google sign-in needed its own accounts
table (`migrations/014_accounts.sql`) and its own role-assignment step
inside Studio, rather than trusting anything Google hands back.

## Flow

1. The frontend sends the person to Google's OAuth consent screen
   (`client_id` from `VITE_GOOGLE_CLIENT_ID`), then lands on `/sso-callback`
   with a `code`.
2. The frontend posts `{code, redirect_uri}` to `POST /api/auth/google`.
3. The backend (`backend/google_auth.py`) exchanges the code for Google's
   access token, reads `userinfo`, and refuses anything Google hasn't
   marked `verified_email: true`.
4. `PostgresRepository.upsert_google_account` creates or refreshes a row in
   `accounts` keyed by email. A **new** account has `global_role = NULL`.
5. The backend signs a short-lived (12h) Studio session JWT
   (`STUDIO_SESSION_SECRET`, HS256) carrying that account's id and whatever
   role it has right now — empty string for a pending account — and
   returns it as `access_token`, plus `pending: true/false`.
6. The frontend sends that token back as `Authorization: Bearer studio:<jwt>`.
   `identity()` in `backend/app.py` validates it and returns an `Identity`
   with an **empty role set** for a pending account, so `require_global`
   denies every route exactly as it would for anyone else with no role —
   a brand-new Google sign-in cannot grant itself access.

## Assigning a role

`GET /api/accounts?role=pending` (admin only) lists accounts waiting on a
role. `POST /api/accounts/{id}/role` with `{"role": "client"}` (etc., admin
only) assigns one; the account's *next* sign-in (or a session refresh)
picks up the new role.

## Configuration

Entirely inert until an operator sets all three (`STUDIO_GOOGLE_ENABLED`,
`STUDIO_GOOGLE_CLIENT_ID`/`_SECRET`, `STUDIO_SESSION_SECRET`); the frontend
only renders the "Continue with Google" button when `VITE_GOOGLE_CLIENT_ID`
is set, so none of this is reachable without real credentials in place.

### Google Cloud OAuth client registration

The redirect URI is never a fixed string: both the browser
(`googleRedirectUri()`, `frontend-next/src/lib/google-sign-in.ts`) and the
backend's token exchange (`body.redirect_uri`, forwarded verbatim to Google
by `GoogleOAuthClient.exchange`, `backend/google_auth.py`) build it as
`<origin>/sso-callback` from whatever origin served the page. So every
origin this flow may run from needs both lines registered on the **same**
Google Cloud OAuth 2.0 Client ID (type: Web application), own project, not
Inscend's:

| Environment | Authorized JavaScript origin | Authorized redirect URI |
|---|---|---|
| Production | `https://studio.datafellowsai.com` | `https://studio.datafellowsai.com/sso-callback` |
| Local development | `http://localhost:5173` | `http://localhost:5173/sso-callback` |
| Local development (loopback) | `http://127.0.0.1:5173` | `http://127.0.0.1:5173/sso-callback` |

Port 8100 (the backend) never appears here — the browser never redirects to
it, only the frontend origin matters for Google's allowlist. A Vercel
*preview* deployment gets a random `*.vercel.app` URL each time, which is
not on this list: the Google button is harmless to leave rendered there
(`VITE_GOOGLE_CLIENT_ID` can be the same value), but clicking it will fail
with `redirect_uri_mismatch` until that exact preview URL is added, so
Google sign-in is effectively production/local-only unless someone adds a
preview URL deliberately.

Google's own OAuth consent screen (branding, scopes shown to the user) is
configured once on the same project; it is what makes this "Data Fellows
Studio," not Inscend, asking for consent.

### Where each variable is set

| Variable | Secret? | Where | Scope |
|---|---|---|---|
| `STUDIO_GOOGLE_CLIENT_ID` | No (sent in the browser URL) | Backend host's env config | All environments it runs in |
| `STUDIO_GOOGLE_CLIENT_SECRET` | **Yes** | Backend host's secret store | All environments it runs in |
| `STUDIO_GOOGLE_ENABLED` | No | Backend host's env config | Set `true` only where the above two are also set |
| `STUDIO_SESSION_SECRET` | **Yes** | Backend host's secret store | All environments it runs in; a different value per environment, never reused from local/dev into production |
| `VITE_GOOGLE_CLIENT_ID` | No, but baked into the public JS bundle at build time — never put the client secret here | Vercel project → Settings → Environment Variables, scoped to **Production** (`studio.datafellowsai.com`) | Production |
| `VITE_GOOGLE_CLIENT_ID` (same value) | No | `frontend-next/.env.local` (gitignored, never committed) | Local development only |

The backend (`backend/`) is FastAPI + PostgreSQL, not a natural fit for
Vercel's serverless functions (no long-lived connections, no persistent
`uvicorn` process) — it needs its own host, decided separately from the
Vercel frontend deployment. Wherever that is, `STUDIO_GOOGLE_CLIENT_SECRET`
and `STUDIO_SESSION_SECRET` go in that host's secret manager, never in a
`.env` file committed to the repo (both are already covered by `.gitignore`;
only `.env.example`, with placeholder values, is tracked).

## What's not built

- No way for an admin to *remove* a role or deactivate an account yet —
  only `POST /api/accounts/{id}/role` to set one.
- No email notification when an admin assigns a role; the person just
  has to sign in again.
- Session tokens aren't revocable before they expire (12h) — there's no
  session table, just a signed claim.
