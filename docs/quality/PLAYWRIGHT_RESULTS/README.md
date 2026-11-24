# Browser verification

The synthetic workflow suite ran against both the memory API and a separate PostgreSQL 16 API. Chromium used the repository's vanilla frontend on loopback. Results are recorded per script and adapter.

| Walkthrough | Verified behavior |
|---|---|
| synthetic-lifecycle | Organization, engagement, project, package, application, qualification fixture, opportunity, interest, selection, invitation, acceptance, submission, independent QA, client acceptance and project completion. An over-budget AI request is denied, an authorized deterministic planning run creates an artifact, self-review is denied and a separate reviewer approves. |
| profile-admission-review | Structured profile and private reference entry, optimistic save, reload, assessment, independent decision, desktop and mobile capture, denied cross-role profile access |
| client-portal | Organization-scoped progress, project message, revision, successor review, version acceptance, completion and denied outsider access |
| admin-mission-control | Four browser widths, project filtering, sorting, detail inspection, focus visibility and denied professional access |
| engagement-workspace | Developer controls hidden at ordinary entry, explicit local harness, real organization selector, engagement creation, search and detail |
| ui-contract | Existing project selector contract and removal of obsolete duplicate selector |

Six distinct scripts passed per adapter. The older profile-onboarding entry point forwards to the same profile walkthrough and is counted once. Some setup and decisions use authenticated API calls. These results do not establish all 21 steps as routine end-user UI journeys. Production sign-in, agreements, formal handover and scanner-backed evidence remain unvalidated.

## Responsive and design gates

The navigation script exercised five synthetic identities at 1440, 1024, 768, 390 and 320px. Each comparison pass covered 185 route/viewport combinations, including native click-through on the updated mobile menu, current-page semantics, document overflow and Escape focus return. PNGs are representative captures; each combination has a layout assertion on the updated shell. The parent capture exercises the original routes using URL navigation.

Impeccable scanned frontend source and the rendered mobile professional entry. The source scan retained three findings covering the existing font declaration and a colored shadow. The mobile entry reported zero findings. This scanner and keyboard smoke test do not establish WCAG conformance. Large-volume performance, assistive-technology testing, failure injection and all-state visual coverage remain outstanding.

## Reproduction

Start the frontend at port 5173 and a local synthetic API. Use a disposable database with migrations 001–008 for PostgreSQL. Set STUDIO_API_URL, STUDIO_ARTIFACT_DIR, NODE_PATH and PLAYWRIGHT_CHROMIUM for the local environment. Run synthetic-lifecycle first, then the profile, client, admin, engagement and UI scripts. Run workspace-navigation after seeding professional-1 through the lifecycle. For a baseline, serve the parent frontend at the same origin, set STUDIO_BROWSER_URL to its index page and STUDIO_BASELINE=1. Capture before and after against the same seeded database.

## Reviewer worklist increment

The revised lifecycle ran once per adapter. A reviewer requested a correction to version 1. The professional submitted version 2 using an accepted assignment. The reviewer inspected the preceding decision and approved version 2. The authorized client accepted that version and the project reached completion. Neither walkthrough reported a page exception or failed request. The reviewer decision was captured at 1440px and 390px.
