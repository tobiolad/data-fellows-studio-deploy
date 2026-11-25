# Decisions and blockers

Founder response received and recorded 25 November 2026 ("Founder Response
to System Audit & Full AI Workforce Build Mandate"). Each of the original
ten items now carries a resolution; new blockers raised by the AI-workforce
mandate itself are appended at the end. Nothing below has been acted on
beyond what's explicitly marked done.

## 1. The premise has moved — RESOLVED

**Founder decision:** keep Google OAuth, Vercel, Railway and Postgres as
the **approved short-term operating arrangement**. Azure remains the
**long-term target**, funded by the Microsoft startup scholarship, but is
not being migrated to now. The documentation must distinguish three
things, not two: current live implementation, approved interim
arrangement, and long-term target. `ARCHITECTURE.md` has been updated to
carry this distinction explicitly (see its new "Three horizons" section).
Identity must be designed so a future provider (Entra, or anything else)
can be added without an auth rewrite — tracked as a Phase 1 requirement,
not an immediate migration.

## 2. The live Stripe key — RESOLVED, action pending

**Founder decision:** keep the integration; rotate the key in a
**controlled** way (verify new permissions, affected integrations,
rollback plan, monitoring, before cutover). Use Stripe **test mode** for
all new automated development/testing from now on. Live payment actions
need explicit authorization each time. Do not interrupt real billing.
**Status: rotation plan not yet written.** This is Phase 0 work — see the
new blocker list below. No key value will ever be pasted into chat, a
commit, or a log; the replacement is created directly in Stripe and
referenced only by its Railway environment variable name.

## 3. `STUDIO_SESSION_SECRET` — RESOLVED, action pending

**Founder decision:** approved, treated as a security priority. Rotate
it, invalidate every session signed with the old value, require affected
users to sign in again, document the expected user impact, and get
explicit confirmation before executing (since Studio is live). **Status:
not yet executed.** Phase 0 item.

## 4. The $1 verification invoice — needs one more fact before closing

Not yet inspected this round. Next action: read the actual Stripe record
for "Send Verification Org" and report back (unpaid test → prepare to
void; paid or tied to a real obligation → report status, propose
accounting action, do nothing automatic). No new invoice will be created
to test anything further.

## 5. Project completion defect — APPROVED TO FIX, not yet done

**Founder decision:** fix it. Must respect the project's actual
completion rules; test multi-package, rejected-package, optional-package
and revision scenarios; run the full regression suite before proposing
anything for merge. **Status: Phase 0, next concrete code change.**

## 6. BizPilot `openai` dependency — APPROVED TO FIX, not yet done

**Founder decision:** fix the packaging problem, but first determine
whether `async_ai_service.py` is active, optional, or dead code, and avoid
unnecessarily introducing a paid-provider dependency while doing it.
Preserve working diagnostic behavior; run BizPilot's tests. **Status:
Phase 0, next concrete code change.**

## 7. Existing pull requests — RESOLVED (hold, with conditions)

**Founder decision:** preserve all work. Keep #3, #4, #5 and #19 held
until their individual conflicts and relevance are resolved one at a
time. Produce an exact reconciliation report (Studio's 38 remaining PRs,
and BizPilot's queue) against the canonical branch and the live deployed
commit, showing what's already merged, what's still useful, and what
conflicts — **before** any merge. Do not resume BizPilot's merge sequence
until its integration baseline is independently verified. **Status: the
reconciliation report has not been produced yet** — it's real work (38
PRs to diff individually), tracked as a Phase 0/ongoing item, not
something to rush to close out this response.

## 8. Legacy `frontend/` — RESOLVED

**Founder decision:** the React frontend (`frontend-next/`) is the
intended product interface. Keep the old `frontend/` until functional
parity, references, build dependencies and rollback needs are checked,
then propose its removal in its own dedicated PR. No action needed now.

## 9. AI product claims — RESOLVED, standing rule

**Founder decision:** describe the AI workforce as under development
until actual agent capabilities are tested. Never claim autonomous
engineering, screening, diagnostics or support are fully available when
they're not; vision and working functionality must stay distinguishable
to a customer. This is now a standing constraint on all customer-facing
copy for the rest of this build, not a one-time edit.

## 10. Hosting reconciliation — RESOLVED

**Founder decision:** document Vercel/Railway/Postgres as an authorized
interim deployment; Azure is the long-term target subject to its own
cost/migration/security review, not happening now. The one near-term
exception: evaluating the Microsoft Foundry model API as a controlled AI
provider is in scope immediately and does **not** require moving the
Studio application itself. Folded into `ARCHITECTURE.md`.

---

## New blockers raised by the AI-workforce mandate (25 November 2026)

These are the items that genuinely cannot proceed without a founder
decision or an external fact the founder is better placed to get. Each is
referenced from the implementation plan delivered alongside this file.

### A. The deploy-repo release process

Vercel and Railway both build from `tobiolad/data-fellows-studio-deploy`
(a separate personal repo), not `Data-Fellows/data-fellows-studio`. Every
commit this session has gone to the latter; none of it has reached the
former, which is why nothing built so far has been visible on the live
site. **A push to that personal repo's `main` deploys to production
immediately — there is no staging in front of it.** I have working push
access and confirmed a clean fast-forward is possible, but per Decision 1
("no production deployment changes without my approval," "establish a
controlled release process that keeps the canonical organization
repository authoritative") I have not pushed it. **Needed from you:**
confirm the release process I propose in the implementation plan below
(canonical repo → reviewed branch → an explicit, named release step that
pushes to the mirror), and tell me whether to execute that first release
now or hold until more of Phase 0 is done.

### B. Microsoft startup scholarship — facts only you can get

The plan calls for verifying, before any Foundry/DeepSeek code is
written: the exact subscription and remaining eligible balance, credit
expiration date, which DeepSeek deployment (if any) is already available
to Data Fellows, whether it's billed directly by Azure or by a partner,
and the model/version/region/endpoint/rate-limit/data-terms. None of this
is discoverable from the codebase or from here without your Azure
portal access or an account conversation with Microsoft. **Needed from
you:** either grant a way to check this (a read-only Azure login, or an
export of the relevant subscription page), or get the answers yourself
and hand them back — I can draft the exact questions to ask Microsoft if
that's faster.

### C. Stripe test-mode credentials for new development

Decision 2 says new automated tests must use Stripe test mode. Today's
billing tests use a fake in-process Stripe double (`_FakeStripeClient`),
which is correct for unit tests, but a real end-to-end test-mode run
(the kind already proven once in live mode this session) needs a real
Stripe **test** restricted key. **Needed from you:** a test-mode
restricted key when we get to re-proving billing end to end, same
scoped-permission template as the live one.

### D. Scope of the first real-model demonstration

Section 14 of your directive asks for one narrow real-model
demonstration after the synthetic one, "after explicit approval and
proof that the DeepSeek deployment is funded appropriately." That
approval is a separate, later decision from this one — flagged here so
it isn't assumed to be pre-granted by this response.
