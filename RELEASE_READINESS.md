# Release readiness

There is no staging environment distinct from production: every push to
the branch Vercel/Railway deploy from goes live immediately
(`SYSTEM_AUDIT.md` §2, §5). "Release readiness" here means **readiness for
wider real-merchant/real-client use**, not readiness of a deploy pipeline,
since the pipeline already runs continuously.

## Current real usage

- **One real Stripe customer, one real sent invoice, one real webhook
  delivery**, all against the live (not test-mode) Stripe key, founder-
  directed and confirmed working this session.
- **Admin/client/professional/reviewer roles have been driven through a
  genuine end-to-end workflow** (signup → application → admission →
  assignment → deliverable → review → acceptance → invoice → support
  request) by this session's own testing, not only by unit tests.
- No other real client or professional is yet onboarded through the
  product as far as this audit can observe from the database/code; the
  billing and diagnostic-handoff proofs used test/founder-controlled
  accounts.

## Go / no-go by area

| Area | Status | Reasoning |
|---|---|---|
| Core auth, multi-tenant isolation | **Go** | Independently re-verified this session, including the new admin-preview feature's boundary |
| Client delivery lifecycle (project → deliverable → review → acceptance) | **No-go without a fix** | The multi-work-package completion defect (P0 #1) can mark a project done prematurely; this is exactly the kind of thing that erodes trust if a real client hits it |
| Billing | **Conditional go** | The feature itself works and is proven live; the open condition is the live-vs-test-key decision (P1 #5), a founder call, not a code gap |
| AI agent/workforce | **No-go for anything beyond the synthetic single-tool path** | Structurally incomplete (P2); nothing currently claims to be more than it is, so this is a scope limit, not a lie to a user — but it is not ready to carry real delivery work |
| Support requests | **Go** for the ticket/resolve loop itself; **No-go** for anything implying triage/SLA, since none exists | Don't market it as more than "a human reads your request and resolves it" |
| Professional admissions | **Go** for the human-reviewed path; the AI-assisted screening step described in planning docs does not exist, so don't claim it | — |
| BizPilot ↔ Studio handoff | **Go** for the one-way creation of a scoped project; **No-go** for any claim of two-way status sync, since read-back isn't built | — |
| Security posture | **Conditional go** | Tenant isolation and input handling are solid; the two open secret-hygiene items (session secret exposure, live Stripe key) are process risks the founder already knows about and must explicitly accept or close, not code defects blocking release |
| Public website integration | **No-go for any claim of integration** | Zero connection exists between `data-fellows-web-app` and Studio/BizPilot; a lead captured on the public site does not reach Studio in any form |
| Design/accessibility polish | **Not evaluated this pass** | Explicitly deferred by the founder's own "functionality first" instruction; not a blocker for internal/founder-supervised use, would want a pass before a broad unsupervised rollout |

## What "ready" would require, minimally, before adding a real paying
## client beyond the founder's own test accounts

1. Fix the project-completion defect (P0 #1) — this is the one item that
   could directly misrepresent delivery status to a real client.
2. Resolve the live Stripe key and session-secret items explicitly (P1
   #4, #5) — accept the risk in writing, or close it.
3. Decide, in writing, what the product will *say* about AI involvement
   in delivery versus what actually happens today (the gap between the
   planning docs' agentic vision and the synthetic-only reality is real
   and should not reach a client's expectations unmanaged).

Everything else in `MASTER_BUILD_CHECKLIST.md`'s P2–P4 can proceed after
or in parallel with onboarding a first real client; none of it is a
precondition for the three items above.
