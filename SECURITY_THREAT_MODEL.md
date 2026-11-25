# Security threat model — verified this session

Scope: Studio (backend + `frontend-next/`) and the BizPilot→Studio handoff
boundary. The master prompt's explicit instruction governs this document:
**never trust a frontend role check as an authorization boundary** — every
item below was checked against the server code, not the UI.

## Assets

1. Client business data (organizations, projects, deliverables, support
   requests).
2. Professional personal/application data.
3. Billing data: Stripe customer ids, invoice contents, webhook secret.
4. Session secrets (`STUDIO_SESSION_SECRET`), OAuth credentials, Stripe
   restricted key, Stripe webhook signing secret.
5. Platform integrity: the ability to act as another tenant, another role,
   or to forge a payment/webhook event.

## Trust boundaries

- Browser (untrusted) → Vercel-served static frontend (untrusted — it is
  attacker-visible source).
- Frontend → Railway-hosted API (trust boundary: every request must prove
  its actor via the session JWT; nothing the frontend asserts about its own
  role is trusted past this point).
- API → Postgres (trusted internal network, Railway-managed).
- API → Stripe (external, authenticated by a restricted API key scoped to
  Customers Write + Invoices Write only).
- Stripe → API webhook endpoint (external, authenticated by HMAC
  signature verification, not by network trust).
- BizPilot → Studio handoff endpoint (external repo, external trust —
  authenticated, idempotent, documented in `docs/diagnostic-handoff.md`).

## Threats considered, and verified disposition

| # | Threat | Disposition | Evidence |
|---|---|---|---|
| T1 | A client reads another organization's data by guessing an id | Mitigated | Every `persistence.py` read method takes the actor id and joins through membership; `test_persistence_api.py` has explicit cross-tenant-denial tests. Re-verified by direct code read this session, not reused from memory. |
| T2 | A non-admin invokes the new admin-preview parameter (`client_overview?organization_id=`) to read any org | Mitigated | `require_global(actor, "admin")` gate added and specifically tested (`test_admin_may_preview_a_specific_organizations_client_overview`): a non-admin passing the param gets 403, not the preview. |
| T3 | The View-As preview silently grants write authority, not just read | Mitigated by design | `useEffectiveRole` only changes what the frontend *renders*; every write path (`accept_deliverable`, invoice creation, etc.) checks the real session's membership/role server-side, independent of any preview state, which is never transmitted to the backend at all — the backend has no concept of "viewing as." Confirmed by reading every write endpoint touched, not assumed. |
| T4 | A forged Stripe webhook updates invoice status without a real payment | Mitigated | `verify_webhook_signature` recomputes HMAC-SHA256 over `{timestamp}.{raw body}` using the real webhook secret, rejects outside a 5-minute tolerance window. Proven against a real Stripe-delivered webhook this session (not just unit-tested). |
| T5 | A replayed/duplicated webhook double-processes a payment event | Mitigated | `stripe_webhook_events(id) ON CONFLICT DO NOTHING` dedup table; `record_webhook_event` returns `False` on a second delivery of the same event id and the handler short-circuits. Proven live. |
| T6 | A client sees a draft invoice before the business sends it | Mitigated | Draft invoices are filtered server-side in the client-facing list/get queries, not merely hidden in the UI; a draft and a nonexistent invoice both return 404 to a client caller (never a 403, which would itself leak existence). Verified by direct code and test read this session. |
| T7 | The live (not test-mode) Stripe key is exposed or misused | **Open, accepted risk, founder-directed** | A real `rk_live_` key is configured. It is a *restricted* key (Customers Write + Invoices Write only — no Payouts, Terminal, Reporting, or broader scopes), which bounds the blast radius of a leak to "could create customers/invoices," not "could move money out." The key itself passed through this chat session in plaintext when the founder pasted it. **This is the single highest-severity open item.** See `DECISIONS_AND_BLOCKERS.md`. |
| T8 | `STUDIO_SESSION_SECRET` exposure lets an attacker forge a session for any actor/role | **Open, previously raised, founder declined rotation** | HS256 signing means anyone with the secret can mint a valid token for any `actor_id`/role. This secret has been visible in this session's history. Founder was informed and declined rotation at the time. Re-flagged here as it meets the master prompt's definition of a security finding that must be named, not silently carried. |
| T9 | A professional or client forges a role elevation via a crafted request body | Mitigated | Role is set exclusively via `set_account_role`, admin-only, never accepted as a field on any self-service signup/profile endpoint. Confirmed by reading every endpoint that writes `accounts.role` or `organization_members.role`. |
| T10 | Prompt injection via client-authored content reaching a model | Not yet applicable / deferred | No real model provider is wired in (`model_gateway.py` refuses non-synthetic providers). This threat becomes live the day a real provider is approved — must be addressed in that same change, not after. |
| T11 | An agent's tool call exceeds its declared scope | Mitigated for the one existing tool | `allowed_tools` is checked as a subset at run creation; only one tool (`planning`) exists today so this is real but minimally exercised. |
| T12 | Malicious file upload (malware, path traversal, oversized payload) | Not applicable yet | No file upload exists anywhere in Studio. Must be designed in, not bolted on, the day uploads are added — this is a pre-registered requirement for that future work, not a current vulnerability. |
| T13 | SQL injection | Mitigated | `persistence.py` uses parameterized queries exclusively; no string-built SQL found in a full read of the file this session. |
| T14 | Cross-tenant leakage via the BizPitol→Studio handoff | Mitigated | Handoff endpoint requires org mapping/authorization and is idempotent against duplicate submission; verified via `docs/diagnostic-handoff.md`'s own description and this session's cross-repo proof run. |
| T15 | Denial of service via unbounded list endpoints / no rate limiting | **Open** | No rate limiting exists anywhere in the API. Low likelihood at current scale (internal tool, small user base), but a real gap before any public-facing surface is added. |
| T16 | Secrets in logs | Partially mitigated | Health/ready endpoints deliberately avoid leaking DB connection details (confirmed by reading them); general application logging was not exhaustively audited this session for accidental secret logging (e.g. a stack trace containing a request body with a token). |
| T17 | An impersonation/View-As session persists after the admin's real session ends | Mitigated | `ViewAsProvider` state lives in `sessionStorage`, scoped to the tab/session and is a pure frontend render preference carrying no backend authorization weight (see T3) — even if it persisted, it grants nothing. |
| T18 | Dependency supply-chain compromise (malicious npm/pip package) | **Open** | No dependency scanning tool configured in either repo that I could find. |

## Residual risk summary

The authorization model (tenant isolation, role checks, object-level
scoping) is the strongest-verified part of the system — it was independently
re-derived from the code this session, not taken on faith, and the new
View-As feature was specifically designed and tested not to weaken it. The
two highest-severity open items are both **secret-handling** issues
(T7, T8) that are organizational/process risks rather than code defects,
and both are already known to the founder. The next-highest-severity
structural gaps (T15 rate limiting, T18 dependency scanning) are standard
pre-launch hardening, not urgent given current traffic, but should not ship
to a wider audience without being closed.
