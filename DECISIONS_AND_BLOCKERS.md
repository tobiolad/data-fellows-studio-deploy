# Decisions and blockers — needs the founder

Everything here needs Tobi's explicit call before work continues on it.
Nothing in this file has been acted on unilaterally.

## 1. The premise has moved — which plan governs now?

The 7 founder-authored planning Google Docs (all dated 24 November,
marked "working draft") describe: Microsoft Entra for auth, Azure as the
eventual (last) deployment target, and explicitly "no live money
movement" as a safety boundary for this phase. Since those docs were
written, this session has, at your direction: built real Google OAuth
(not Entra), deployed to Vercel + Railway (not Azure), and processed a
real transaction through a live Stripe key. **None of this was a mistake
or scope creep — you directed every step.** The question is whether the
planning docs should be updated to match what's actually true, or whether
there's a reason Entra/Azure/no-live-money is still the intended
destination and today's stack is a temporary bridge. This governs whether
`ARCHITECTURE.md` and the other audit files should be read as "the plan"
or "a snapshot of a detour." **Needs your answer before any of the docs
are revised to be forward-looking rather than descriptive.**

## 2. The live Stripe key

A real `rk_live_` restricted key (Customers + Invoices write only) is
configured and has processed one real invoice. You said "let's use it
like that" when I flagged it was live, not test. Flagging again now that
the full audit is in front of you: this key, if ever exposed, could
create customers and invoices in your real Stripe account (not move
money out — it has no Payouts/Charges scope). Options: leave it as is
(it's already working and scoped narrowly), rotate it periodically as a
habit, or move to test mode until real clients are onboarded. **No action
taken; your call.**

## 3. `STUDIO_SESSION_SECRET` exposure

This secret has appeared in this chat's history. You were told before and
declined rotation. Re-raised here only because the master audit asked
every open security item be named, not because anything new happened.
**If you still want to leave it as is, no action needed — just confirming
that's still the decision.**

## 4. The $1 test invoice under "Send Verification Org"

Still open in live Stripe from earlier verification. Void it, or let it
sit — low stakes, but it's real and in your live account. **Needs a
one-line answer, not a build task.**

## 5. Project completion defect (P0)

Confirmed still present: a project with multiple required work packages
is marked complete when any one deliverable is accepted, not all of them.
This is a real correctness bug that could misrepresent delivery status to
a client. **Recommend fixing this before anything else** — it's small,
contained to one function (`project_complete` in `persistence.py`), and
every day it ships is a day a real engagement could be marked done
prematurely. Waiting for your go-ahead to fix it, per your instruction not
to begin new work until the audit baseline is approved.

## 6. BizPilot's `openai` dependency gap

`async_ai_service.py` can't even be imported without the `openai` package,
which isn't declared. Small fix (add the dependency or make the import
lazy), but I want your confirmation before touching BizPilot's
`requirements.txt`, since that file's dependency set may be deliberately
pinned for a reason I don't have visibility into.

## 7. The PR backlogs

- Studio: 38 stacked draft PRs still open (task #34), explicitly paused
  by your "do not close/merge/delete without approval" instruction this
  round. The earlier close-14-of-53 effort (and the self-corrected #3/#4/#5
  mistake) are both already resolved; this is just the remaining count,
  frozen until you say go again.
- BizPilot: its own PR-stack merge sequence (task #7) was never approved.
  Same status — paused, not forgotten.

**Needs**: either explicit approval to resume closing/merging, or a
decision to leave both backlogs as they are for now.

## 8. `frontend/` vs `frontend-next/`

The old `frontend/` directory in Studio is dead — not built, not deployed,
not referenced anywhere. Recommend deleting it so a future reader doesn't
mistake it for live code, but it's your repo's history to decide, not
mine to delete silently.

## 9. What the product says about AI, versus what it does

The planning docs describe a genuinely agentic workforce — AI screening
applicants, AI investigating support incidents, AI planning projects. None
of that exists yet; what exists is one synthetic, instantaneous
"planning" agent type behind a real tool-authorization and reviewer-
approval boundary. This isn't a problem by itself, but if any client-
facing copy, pitch material, or the public website ever describes more
than this, that's a promise the product doesn't keep yet. **Needs a
decision on messaging, not code** — happy to help draft accurate copy
once you've said how far ahead of the build you want the story to run.

## 10. Hosting reconciliation, formally

The master prompt asked me to "first reconcile the current hosting
arrangement with the founder" before describing it as settled. This
document, together with #1 above, is that reconciliation request:
Vercel + Railway + Google OAuth + live Stripe is what's actually running
today, for all three repos, entirely at your direction. If that's the
plan going forward, say so and I'll treat the older docs as superseded
history rather than a target to reconcile toward. If it isn't, tell me
what changes and why, and I'll fold that into the next revision of these
audit files.

---

**Per your instruction, no further build work (including the paused
admin View-As feature, the PR backlogs, or any item in
`MASTER_BUILD_CHECKLIST.md`) will resume until you've reviewed the audit
baseline above and told me what to do next.**
