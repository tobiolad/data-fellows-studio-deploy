# Master build checklist — prioritized

Derived from `REQUIREMENTS_TRACEABILITY.md`'s full gap list. Ordered by
risk and dependency, not by effort. Each item names its tracking task
number where one already exists in this session's task list.

## P0 — correctness defects already shipped, fix before anything else

1. **Multi-work-package project completion defect** (task #15). A project
   with several required work packages is marked complete when *any one*
   deliverable is accepted, not when *all required* ones are. This is a
   live correctness bug in a delivery product, not a gap — it can tell a
   client or the founder a project is done when it is not. Fix:
   `project_complete` in `persistence.py` must check every required work
   package's own acceptance state.
2. **BizPilot `openai` missing dependency** (new, found this session).
   `backend/services/async_ai_service.py` cannot even be imported in an
   environment matching `requirements.txt`. Fix: declare the dependency,
   or make the import lazy/optional if the module must work without it.
3. **Studio integration-test isolation gap** (new, found this session).
   The suite silently produces false failures when run twice against the
   same un-truncated database. Fix: either the fixtures truncate
   between tests, or the suite documents "always use a throwaway database"
   loudly enough that a developer doesn't mistake drift for a regression.

## P1 — security/secret hygiene, already known, not yet closed

4. **Rotate `STUDIO_SESSION_SECRET`** — it has been visible in this chat
   session's history. Founder was told and declined; re-raised here per
   the master prompt's instruction to name every open security item
   plainly rather than let a past "no" silently retire it.
5. **Decide the live Stripe key's disposition** — it is a real `rk_live_`
   key, restricted in scope, already used for a real invoice. Confirm
   intentional, or move to test mode / rotate.
6. **No rate limiting anywhere in the API** — low urgency at current
   traffic, real exposure before any wider release.
7. **No dependency/vulnerability scanning configured** in either repo.

## P2 — structural gaps blocking the agentic vision specifically

8. **Background job queue / worker process** (relates to task #13). Every
   current "agent run" is a synchronous, instantaneous call because there
   is nowhere for a longer one to live. This blocks essentially every
   item in §5 and §10 of `REQUIREMENTS_TRACEABILITY.md` — it is the single
   highest-leverage piece of infrastructure to build next if the AI
   workforce is the priority.
9. **A second real agent/tool type**, to actually exercise tool-registry
   authorization, agent-to-agent handoff, and retry/cancel semantics
   beyond the trivial single-tool case they're currently tested against.
10. **Approved real model provider** (task's prerequisite is a founder
    decision, not code) — `model_gateway.py` is ready to take one; nothing
    is approved today.

## P3 — real product gaps named explicitly in the master prompt

11. **Diagnostic handoff read-back** (task #14) — `Diagnostics.Summary.Read`
    / `Diagnostics.Handoff.Read` from the contract are unimplemented on the
    Studio side.
12. **File storage, quarantine, malware scanning** — does not exist at
    all; needed before any upload feature ships.
13. **HubSpot company/deal mapping, proposals/SOW, project budgets,
    professional compensation** — none of this exists; large, should be
    scoped as its own phase (relates to task #17).
14. **Reviewer/AI-assisted professional screening** — applications are
    reviewed entirely by a human today; no AI touches the admission
    pipeline (Phase Three, task #12, not started).
15. **Support ticket severity/SLA/incident lifecycle** — the ticket itself
    shipped this session; everything around it (severity, escalation,
    post-incident review) does not exist (task #18).

## P4 — polish, explicitly deferred by the founder's own sequencing

16. Visual/UX design pass per portal (tasks #8–#11) — founder's own
    instruction this session was "prioritize everything working first,"
    so this was correctly deferred, not skipped by oversight.
17. Decide and execute the `frontend/` (legacy) vs `frontend-next/` cutover
    (task #25) — low risk, mostly a delete, but should be a deliberate
    decision with the founder rather than silent.
18. Close the remaining 38 stale stacked draft PRs on Studio (task #34) —
    explicitly paused by the master prompt's new instruction not to
    close/merge/delete without approval. Needs fresh explicit sign-off,
    separate from the earlier one.
19. Approve BizPilot's own PR-stack merge sequence (task #7) — same
    status: paused pending explicit approval, not forgotten.

## Sequencing note

The master prompt's own direction — "prove the entire lifecycle before
expanding; do not create nine empty agent profiles" — argues for doing
P0 and P1 first (they are regressions/hygiene, not new scope), then P2
item 8 (the worker/queue) before any of P2's other items or P3's AI-touching
items, since nothing else agentic can be real without it. P3's non-agentic
items (file storage, HubSpot, billing depth) can proceed in parallel on a
separate track since they don't depend on the worker/queue.
