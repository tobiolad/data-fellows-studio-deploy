# Studio integration plan — status check and owner recommendation

Checked 24 November 2026, two days after `docs/release/PR_INTEGRATION_AUDIT.md`
was written. This is a status refresh, not a re-audit: it confirms that
document's findings still hold, folds in the new PR this session opened, and
gives a single actionable recommendation. It does not merge anything.

## What changed since the 22 November audit: nothing load-bearing

- `main` is still at `c022f177` — the exact commit the audit recorded "at
  intake." Verified via `gh api repos/data-fellows/data-fellows-studio/commits/main`.
- Zero PRs have merged (`gh api .../pulls?state=closed` with `merged_at`
  filter returns empty).
- The PR chain is unchanged: 54 open draft PRs, each one's base equal to the
  previous PR's head, exactly as the audit described (re-verified directly
  against the GitHub API, not re-derived from the audit document).
- One addition: **PR #55**, opened this session, based on PR #54's head
  (`codex/studio-release-verification`), adding an AI agent registry and
  model gateway. `gh api` reports it `mergeable: true`, `mergeable_state:
  clean` against its base. It is new work, not part of the audited #1–#54
  chain, and should be reviewed and merged **after** that chain reaches its
  base, not interleaved with it.

## Recommendation: execute the existing audit's sequence as written

The 22 November audit's four-step owner merge sequence is still the right
plan and does not need to be redesigned:

1. **Protect `main`** (require review, status checks, restrict workflow
   edits) before merging anything. GitHub still reports `main` unprotected.
   This is the one concrete action item with no dependency on anything
   else — it can happen today, independent of any PR review.
2. Integrate `#1 → #2 → #6..#18 → #20..#48` in ascending order within each
   range, retargeting each child after its parent lands and re-checking the
   new merge base before continuing.
3. Integrate `#49 → #50 → #51 → #52 → #53 → #54`.
4. **Then** review and integrate `#55` (this session's AI agent registry
   work) against whatever `main` has become by that point — it will very
   likely need a mechanical rebase at that point, since it currently targets
   `codex/studio-release-verification` directly rather than a moving `main`.
5. Hold `#3`, `#4`, `#5`, `#19` for manual, owner-directed disposition, per
   the original audit's file-conflict findings
   (`backend/app.py`/`auth.py`/`test_app.py`/`test_auth.py`, plus frontend
   and CI files for #5). Having now read `backend/auth.py` and `backend/app.py`
   directly myself this session, the hold recommendation is architecturally
   sound: the current Entra integration (`EntraTokenValidator` /
   `HttpJwksProvider` in `backend/auth.py`) and the admission/auth model in
   `app.py` are materially different from — and more complete than — what a
   pre-PostgreSQL-era Entra PR would contain. Porting individual behaviors
   out of #3/#4/#5/#19 rather than merging them wholesale remains the right
   call.

## What this session did not (re-)do

- Did not re-run the merge-tree simulation the original audit performed; a
  shallow-clone attempt at a spot-check hit `fatal: refusing to merge
  unrelated histories` (an artifact of shallow fetch depth, not evidence of
  anything). The original audit's conflict list is corroborated instead by
  independently reading the relevant files this session and confirming the
  hold rationale makes sense given their current content.
- Did not merge, rebase, or retarget any PR. Did not change branch
  protection (requires org-level permissions this session was not asked to
  use).
- Did not re-verify the migration-checksum table in the original audit;
  this session's own migration (`011_agent_registry.sql`, added in #55) is
  new and additive and was not part of that table's scope.

## Next action for the owner

Protect `main`, then begin step 2 of the existing sequence. No further
analysis is blocking that start.
