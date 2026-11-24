# Design Skills Evaluation

Reviewed 2026-11-21 against the current Studio static frontend and the Codex execution environment.

| Skill | License / release | Fit | Decision | Security notes |
|---|---|---|---|---|
| [Impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0; npm `4.10.0`; Node >=18.19 | Strong fit for an existing Operate UI; deterministic detector and responsive/browser review | Installed project-locally under `.agents/skills/impeccable` with the version-pinned npm installer; hooks intentionally not enabled | The launcher can download a self-contained engine into `~/.impeccable`; no account or API key is required for detection. Do not use live mode or remote copy-edit fallback without review. |
| [Unslop](https://github.com/heydamir/unslop) | CC BY 4.0; pinned commit in `skills-lock.json` | Good targeted critique for existing dashboards and portals | Installed project-locally under `.agents/skills/unslop`; manual activation only | Its optional snapshot/story scripts use Playwright and may accept URLs. Use only localhost/synthetic data; do not connect image services or paid generation. Attribution is required for copied/adapted material. |
| [Hallmark](https://github.com/Nutlope/hallmark) | MIT; `2.0.0` | Useful for new/public pages, but heavier for this established internal app | Evaluated, not installed | The skill is Together-AI-oriented and its install scripts copy references/scripts and may run project hooks. No need to add that network or provider dependency to Studio. |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill) | MIT; `2.5.1` | Better for public Data Fellows website work than dense operational UI | Evaluated, not installed | Its gate hooks and optional image/asset workflows are inappropriate for internal synthetic data. Reserve for the public website after a separate review. |

## Activation

- Primary: `$impeccable critique the Admin Mission Control` or `$impeccable audit`.
- Targeted refinement: `$unslop the Admin Mission Control project queue`.
- The skills are project-scoped and committed for reproducibility. No global install, automatic hook,
  live overlay, provider login or paid generation is enabled.
- Browser checks must use the local synthetic frontend/backend only. Never pass client URLs,
  confidential evidence or production credentials to a skill.

## Why the hooks are off

The Impeccable installer offers Codex hooks that execute a launcher after edits and at stop. The
launcher is reviewed and version-pinned, but automatic execution is not needed for this repository
and could add latency or download a binary implicitly. CI and the explicit detector command remain
the release gate.

## Licenses

The project-local skill files retain their upstream front matter and license declarations. Any
future copied reference material must retain the upstream attribution and license notice.
