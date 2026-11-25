# System audit — 25 November 2026

Performed in response to the founder's master audit directive. Supersedes nothing;
it reconciles `docs/release/PR_INTEGRATION_AUDIT.md` (22 Nov), `docs/release/INTEGRATION_PLAN_STATUS_2026-11-24.md`
(24 Nov) and `docs/engineering/CLAUDE_CONTINUATION.md` against what has actually
happened since, including inside this same session.

## 1. The most important finding: the premise has moved

The seven source documents (Human + AI Workforce Architecture, Studio Operating
Model, AI Workforce Strategy & Agent Governance, Studio & BizPilot Product
Architecture, Product Roadmap & Build Tracker, AI Professional Vetting &
Assessment Policy, Managed Client Delivery Playbook — all v0.1, dated 24 November
2026, read directly from Google Docs for this audit) describe Studio as still
at the Phase 0 audit stage, with PR #54 as the last known checkpoint, Entra as
"the planned identity provider," Azure as the only deployment target ("comes
last... before it happens, the owner must approve"), and explicitly "No live
money movement."

**None of that is still true, and the founder made each change personally, in
real time, in this session:**

- PR #55 (an AI agent registry this session built on top of #54) was reviewed
  and **merged into `main`** on 24 November, on the founder's explicit
  instruction ("merge the PRs well"), as commit `b53e9144785a6b0663ed8d505f776a339e67a737`.
  `main` has since taken two further commits (`8707190`, `f66ff4d`) on
  `claude/studio-ai-execution-handoff-8y0l2a` — see §2.
- Identity is **Google OAuth, not Entra** — a founder decision made mid-session
  ("Google-direct, Studio owns accounts/roles"), fully implemented
  (`backend/google_auth.py`, migration `014_accounts.sql`).
- **Studio is live in production right now** at `studio.datafellowsai.com`
  (Vercel) with a real backend on Railway, a real Postgres database, and a
  real admin account (the founder's own Google account) that has signed in
  and used it. This happened in this session, with the founder executing or
  directly approving every step (Google Cloud Console setup, Vercel project,
  Railway service, DNS, the admin bootstrap).
- **Stripe is live, not test-mode, and has already moved real money status**:
  the founder generated a live (`rk_live_...`) restricted key, I set it on
  Railway, and — with the founder's explicit advance knowledge and agreement
  that this would happen — created a real Stripe customer and sent a real
  $1.00 invoice that was delivered and (per the founder) received. This
  directly contradicts "No live money movement" in the Product Roadmap
  document's Phase 6. This is a **conflict the founder created knowingly**,
  not a drift Claude should have caught and didn't — but the planning
  documents are now stale on this point and should be corrected or
  explicitly superseded, not treated as still governing.
- Deployment did **not** go to Azure. It went to Vercel (frontend) and Railway
  (backend), via a personal mirror repository (`tobiolad/data-fellows-studio-deploy`)
  because Vercel's Hobby plan blocks deploying from a private
  organization-owned repo. This was the founder's own choice among options I
  presented, after a full secret-history scan found nothing exposed. It is a
  real, working arrangement, not a mistake — but it is unusual enough that
  it belongs in §7 as something to explicitly ratify or replace.

**What this means for this audit:** I am not treating the master prompt's
scenario (pre-deployment, Entra-planned, no money moved) as the current
state, because it verifiably is not. I am reporting what is actually true,
flagging the gap between the planning documents and reality, and asking the
founder to explicitly reconcile them in §10 — exactly as the master prompt's
own "flag conflicts" instruction asks for.

## 2. Verified repository and deployment state

| Fact | Value | How verified |
|---|---|---|
| Studio canonical `main` HEAD | `b53e9144785a6b0663ed8d505f776a339e67a737` | `gh api repos/Data-Fellows/data-fellows-studio/commits/main` |
| Studio GitHub default branch | `codex/studio-foundation` (still, not `main`) | `gh api repos/.../data-fellows-studio` |
| Branch protection on `main` | Could not read via API (`403 Resource not accessible by integration`) — not confirmed either way; needs checking by someone with admin:repo_hooks scope, e.g. in the GitHub UI | `gh api repos/.../branches/main/protection` |
| CI on current `main` HEAD | `backend`, `containers`, `secrets` all green | `gh api repos/.../commits/main/check-runs` |
| Open Studio PRs | 38 (see §3) | `gh api` pull listing |
| Held PRs #3, #4, #5, #19 | **Reopened this session** after I mistakenly closed #3/#4/#5 during cleanup on 24 Nov; corrected with an explanatory comment on each and left open per the original audit's hold instruction. #19 was never closed. | Direct `gh api` state check + my own correction, logged on each PR |
| Deployed backend | Railway, service `backend`, domain `backend-production-a5267829.up.railway.app`, tracking `tobiolad/data-fellows-studio-deploy` `main` (mirrors `claude/studio-ai-execution-handoff-8y0l2a`) | Railway MCP; redeployed and verified live this session |
| Deployed frontend | Vercel project `data-fellows-studio`, custom domain `studio.datafellowsai.com`, same source branch | Vercel MCP; redeployed and verified live this session |
| Live commit actually running in production | `f66ff4d150bbcf34132b47aeaaf83c4b9927feb0` (on `claude/studio-ai-execution-handoff-8y0l2a` / the personal mirror's `main`) — **ahead of** the canonical repo's `main` | `gh api` + Railway/Vercel deployment metadata |
| bizpilot-pro-concept default branch / HEAD | `main` / `92a441a0` ("Merge pull request #3...", 20 Nov) | `gh api` |
| bizpilot-pro-concept open PRs | 14 (`#1`–`#16`, a stacked chain similar to Studio's original shape) | `gh api` pull listing |
| data-fellows-web-app HEAD | `868f792` (24 Nov, active, unrelated recent work) | `gh api` |
| Studio ↔ public website integration | **None found.** No file in `data-fellows-web-app` references `studio.datafellowsai.com`, `data-fellows-studio`, or any `STUDIO_*` variable. | `grep` across the repo |

**Canonical `main` is behind what's deployed.** The founder's explicit
instruction this session was "develop on `claude/studio-ai-execution-handoff-8y0l2a`,
push to no other branch without explicit permission." The one exception
granted was the PR-stack merge into `main` (now `b53e914`). Two further
increments (client billing, workflow-gap fixes, Support) landed only on the
feature branch and its personal-mirror deployment target, which is correct
under that instruction but means **the canonical org repository's `main` does
not contain the code actually running in production.** This needs a founder
decision in §10: merge the feature branch into canonical `main` again, or
treat the personal mirror as the release branch going forward, or something
else.

## 3. PR-by-PR status (Studio)

Already reconciled and current as of this audit — see
`docs/release/PR_INTEGRATION_AUDIT.md` for the original per-PR table and
`docs/release/INTEGRATION_PLAN_STATUS_2026-11-24.md` for the first refresh.
This audit's own update:

- `#1`, `#2`, `#55` — merged (the real, audited content landed via one
  ancestry-preserving merge of PR #55 into `main`, after an earlier mistaken
  squash-merge of #1 was corrected with a revert commit).
- `#6`–`#18`, `#20`–`#54` minus `#19` (49 PRs) — their content is an ancestor
  of what merged; 14 of them (`#6`–`#16`) were closed this session with an
  explanatory comment. **35 remain open** and still need the same
  housekeeping (tracked as Studio task #34); nothing is lost by closing them,
  since their content already landed.
- `#3`, `#4`, `#5`, `#19` — **open, correctly held**, per the original
  audit's file-conflict finding against the Entra/Postgres line. Not
  resolved by this audit; still need the founder's individual review the
  original audit called for.

## 4. Test evidence (reproduced today, not assumed)

**Studio backend** — `python3 -m unittest discover -s backend -p 'test_*.py'`
against a freshly created local PostgreSQL 16 database:
**116 passed, 0 failed, 0 skipped.** (Historical counts of 43/53/58/63 in
earlier documents are checkpoints of earlier, smaller states of the code —
not reproduced as 116 today, and not contradicted; the suite has grown.)

**Studio frontend** — `tsc -b && vite build`: clean typecheck, build
succeeds (`dist/assets/index-*.js` at 911 kB raw / 271 kB gzip — one
non-blocking bundle-size warning, see §9).

**BizPilot backend** — `python3 -m pytest backend/tests/test_diagnostics.py
backend/test_efficient_data_operations.py` against a fresh local PostgreSQL
16 database (`BIZPILOT_DATABASE_URL`): **26 passed, 0 failed.** Reproduces
the "16-test claim" (`test_diagnostics.py`) exactly, plus 10 more in the
other file.

**BizPilot — real defect found**: `backend/test_performance.py` cannot even
be collected — `backend/services/async_ai_service.py` does `from openai
import AsyncOpenAI`, but `openai` is not in `backend/requirements.txt`. This
is either an undeclared dependency (packaging defect) or dead code never
exercised by a real install. Not fixed by this audit; recorded in
`DECISIONS_AND_BLOCKERS.md`.

**BizPilot frontend** — `npm run build` (Next.js): succeeds, static export,
no errors.

**Grep for real AI provider code in Studio** (`openai\.|anthropic\.|api_key.*sk-|ANTHROPIC_API_KEY|OPENAI_API_KEY`
across `backend/`, excluding tests): **zero hits.** No real model provider
is wired into Studio anywhere. Confirms `docs/ai-execution.md`'s own claim.

**Not reproduced in this audit** (carried over as still-open from earlier
reports, nothing new found to contradict them): the Chromium/Playwright
accessibility and role-journey walkthroughs in `docs/release/STAGING_RELEASE_REPORT.md`,
actual Microsoft Entra tenant sign-in (moot now — Google OAuth replaced it
for the path actually shipped), Azure inventory/RBAC, gitleaks history scan
(already run once this session during the repo-visibility decision; found
nothing live to rotate).

## 5. Security and architecture findings

1. **Corrected my own error**: PRs #3/#4/#5 were closed as "superseded" on
   24 November when they should not have been — see §3. Reopened and
   corrected with a comment on each before writing this audit.
2. **Production is live with no staging gate.** There is no separate staging
   environment between a merge/push and `studio.datafellowsai.com`. This
   matches the founder's own operating pattern elsewhere (Inscend's AGENTS.md,
   which is a different product but the same founder, states "a merge to
   main is a release" with the same shape) — but it is worth the founder
   explicitly naming as the accepted model for Studio too, since the
   Product Roadmap document assumes a staging rehearsal gate that doesn't
   exist for the path actually used.
3. **Live Stripe key, no webhook-secret rotation plan on record.** The key
   and `STRIPE_WEBHOOK_SECRET` are both live and working (verified: real
   draft invoice created, real send, real webhook signature round-trip).
   No incident-response note exists yet for "what happens if this key
   leaks" beyond the general session-revocation document for auth tokens.
4. **Branch protection on `main` is unverified**, not confirmed absent — the
   API call that would prove it either way returned 403 for this session's
   permissions. This needs a person with repo admin access to check in the
   GitHub UI.
5. **Two unrelated deployment paths coexist in the repo**: the original
   container/Azure-oriented one (`ops/`, `frontend/`'s own Dockerfile,
   `docs/container-packaging.md`, `docs/staging-runbook.md`) — fully
   present, tested at the container-build level, **never actually used** —
   and the one actually live (Railway running `backend/Dockerfile` directly,
   Vercel building `frontend-next` from source with no container at all).
   The old `frontend/` (vanilla JS) is untouched and not deployed anywhere.
   This is not a defect by itself, but it means roughly half the
   deployment-related documentation in `docs/` describes a path nothing
   currently uses.
6. **No real AI provider is active anywhere** (confirmed by grep, §4) —
   consistent with every planning document's requirement that real-model
   use needs separate approval.
7. **Multi-tenant isolation**: spot-checked via the new admin "View as"
   feature's own test (`test_admin_may_preview_a_specific_organizations_client_overview`),
   which asserts a real client calling the admin-only override parameter
   is refused with 403 — i.e., the isolation boundary was specifically
   tested against the one new surface built this session that could have
   weakened it, not just assumed.

## 6. Conflicts between existing code and the intended architecture

- **Identity**: all seven planning documents assume Entra. The shipped,
  live path is Google OAuth. `frontend-next`'s Entra-era synthetic picker
  is already hidden in production; `backend/auth.py`'s Entra validator
  still exists and is exercised by its own tests, but nothing live uses it.
- **Deployment target**: all planning documents assume Azure, last, after
  explicit approval. The live path is Vercel + Railway, approved in this
  session by the same founder, through a personal-repo workaround. Azure
  readiness work (`docs/azure-staging-readiness.md`, the bizpilot Azure
  inventory PRs) is real and tested at the inventory/dry-run level but
  disconnected from what's actually running.
- **"No live money movement" (Phase 6)** vs. a live Stripe key already in
  use (§1). Needs the founder to either update that document or explicitly
  ratify the exception taken.
- **BizPilot's PR narrative (14 open PRs, titles implying pricing
  intelligence, Tavily/Exa research, Azure staging, cross-case reporting)
  vs. actual code volume**: the diagnostics core is real and substantial
  (≈7,300 lines across 19 files, 26 reproducible passing tests) — not
  fabricated — but I have not individually verified each of the 14 PRs'
  claims against their diffs the way the Studio stack was verified. That
  is Studio task #7 ("Owner: approve PR-stack merge sequence for BizPilot"),
  still pending, and is the natural next audit target if the founder wants
  the same rigor applied there that was applied to Studio's 55-PR stack.

## 7. Decisions needed from the founder

See `DECISIONS_AND_BLOCKERS.md` for the full list with owners and defaults.
Headline items: ratify or correct the "no live money" and "Azure-last"
language in the planning docs against what's already shipped; decide
whether canonical `main` should be brought up to what's actually deployed,
or whether the personal-mirror/feature-branch arrangement is the accepted
release path going forward; decide #3/#4/#5/#19's individual disposition;
confirm `main` branch protection by someone with admin access.

## Related records

`REQUIREMENTS_TRACEABILITY.md` (checklist-by-checklist status against the
master prompt's §4–§15), `MASTER_BUILD_CHECKLIST.md` (prioritized,
single list), `ARCHITECTURE.md`, `SECURITY_THREAT_MODEL.md`,
`TEST_EVIDENCE.md`, `RELEASE_READINESS.md`, `DECISIONS_AND_BLOCKERS.md`.
