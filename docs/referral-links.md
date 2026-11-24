# Referral links

Lets Data Fellows track clients an onboarded partner (e.g. an accelerator)
brings in, and lets the partner see their own link's performance without a
Studio account.

## Creating a link

`POST /api/referral-links` (admin only) with `{"partner_name": "..."}`
returns a row with two distinct secrets:

- `code` — the public, shareable part. A visit to `/r/<code>` on the
  frontend records a visit (`POST /api/referral-links/<code>/visit`, no
  auth — this is meant to be hit from a public landing page).
- `view_token` — a separate, longer secret only the partner gets. Visiting
  `/r/view/<view_token>` on the frontend (`GET /api/referral/<view_token>/stats`,
  no auth) shows them their own visit/signup counts. It is not the same
  value as `code` so sharing one never exposes the other.

## Signups

Organizations in this system are still admin-created only — there is no
public self-serve signup form anywhere in Studio. So "signup" here means:
when Data Fellows staff onboard a new client organization that came through
a partner, they pass that partner's `code` as `referral_code` on
`POST /api/organizations`, and a `signup` event is recorded against that
link with the new organization's id. An invalid or missing code never blocks
organization creation — it's a best-effort attribution, not a gate.

## What's not built

- The public landing page itself. `/r/<code>` in `frontend-next/` only
  records the visit and shows a static message — the real destination
  (the public marketing site, or a lead-capture form) doesn't exist yet.
- Disabling a link (the schema supports `status = 'disabled'`; no endpoint
  sets it yet).
- Any payout or commission logic — this only tracks attribution, nothing
  financial.
