# Implementation branches

The verified open stack is #40 → #41 → #42 → #43 → #44 → #45. PR #41 provides the design system, #42 the client portal, #43 shared vertical slices, #44 persistent profiles, and #45 profile review. Each PR targets the preceding head.

1. [Admission policy PR #46](https://github.com/Data-Fellows/data-fellows-studio/pull/46) targets #45. It hardens stored admission decisions and provides names and admission state for the UI.
2. [Workspace implementation PR #47](https://github.com/Data-Fellows/data-fellows-studio/pull/47) targets `codex/studio-admission-policy`. The updated browser fixtures use the canonical review contract. Both branches are additive and introduce no migrations.

Review the backend and UI together before releasing the changed admission contract. Empty-body approval clients must move to a reviewed profile and reasoned decision.

The reviewer worklist branch `codex/studio-reviewer-worklist` builds on #47 and uses the existing deliverable, membership and review schema.
