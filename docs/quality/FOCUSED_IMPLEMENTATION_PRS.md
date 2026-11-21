# Implementation branches

The verified open stack is #40 → #41 → #42 → #43 → #44 → #45. PR #41 provides the design system, #42 the client portal, #43 shared vertical slices, #44 persistent profiles, and #45 profile review. Each PR targets the preceding head.

1. [Admission policy PR #46](https://github.com/Data-Fellows/data-fellows-studio/pull/46) targets #45. It hardens stored admission decisions and provides names and admission state for the UI.
2. The workspace implementation branch `codex/studio-workspace-navigation` targets `codex/studio-admission-policy`. The updated browser fixtures use the canonical review contract. Both branches are additive and introduce no migrations.

Review the backend and UI together before releasing the changed admission contract. Empty-body approval clients must move to a reviewed profile and reasoned decision.
