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

Entirely inert until an operator sets all three:

- `STUDIO_GOOGLE_ENABLED=true`
- `STUDIO_GOOGLE_CLIENT_ID`, `STUDIO_GOOGLE_CLIENT_SECRET` — from Studio's
  own Google Cloud OAuth client, not a borrowed one, so the consent screen
  says "Data Fellows Studio."
- `STUDIO_SESSION_SECRET` — signs the session JWT; unrelated to Entra's
  keys.

The frontend only renders the "Continue with Google" button when
`VITE_GOOGLE_CLIENT_ID` is set, so none of this is reachable without real
credentials in place.

## What's not built

- No way for an admin to *remove* a role or deactivate an account yet —
  only `POST /api/accounts/{id}/role` to set one.
- No email notification when an admin assigns a role; the person just
  has to sign in again.
- Session tokens aren't revocable before they expire (12h) — there's no
  session table, just a signed claim.
