# Studio integration audit

Reviewed 22 November 2026. At intake, main was c022f177, with 48 open draft PRs. All 48 had successful advertised-base checks and GitHub reported them mergeable into their own base. A local ancestry check and merge-tree simulation against #48 found four divergent heads. This audit also lists the first five release increments. GitHub branch metadata reported main unprotected. Studio had zero configured environments.

## Owner merge sequence

1. Protect main and require review, status checks and trusted workflow changes. Preserve branch heads until the full stack is integrated. Record the reviewed head and tree before each merge.
2. Review and integrate #1 → #2 → #6 through #18 → #20 through #48, in ascending order within each range. Prefer merge commits preserving ancestry. After each parent reaches main, retarget its child, inspect the new merge base and diff, and require passing checks on that new base. Stop on an unexpected tree or scope change.
3. Review #49 → #50 → #51 → #52 → #53, followed by the verification PR containing this audit. The coordination API requires migrations 009–010 and effective assignment scope. The staged web container must serve the new JS module. The job and readiness checks require the packaged migration files. Qualification policy v2 requires the updated approval client and fixtures.
4. Hold #3–#5 and #19 for owner disposition. The earlier Entra, invitation and portal implementations overlap the later PostgreSQL line. Compare any unique behavior with #11, #13, #15 and #48. Review the separate AI portal against the current execution/reviewer model before porting individual changes. Neither a green check nor a conflict-free advertised base proves compatibility with the release head.

## PR-by-PR review

The hold rows list file conflicts from merge-tree against #48. These simulations did not change branch references. The other original PR heads are ancestors of #48.

| PR | Base | Reviewed head | Change | Integration assessment |
|---|---|---|---|---|
| [#1](https://github.com/Data-Fellows/data-fellows-studio/pull/1) | main | `167c546a` | Bootstrap secure managed-delivery foundation | On #48 ancestry |
| [#2](https://github.com/Data-Fellows/data-fellows-studio/pull/2) | #1 | `19a48003` | Add PostgreSQL persistence foundation | On #48 ancestry |
| [#3](https://github.com/Data-Fellows/data-fellows-studio/pull/3) | #2 | `6eacbb6d` | Add configurable Entra token validation | Hold · `backend/app.py`, `backend/auth.py`, `backend/test_app.py`, `backend/test_auth.py` |
| [#4](https://github.com/Data-Fellows/data-fellows-studio/pull/4) | #3 | `3b541852` | Add managed-delivery invitation and dependency gates | Hold · `backend/app.py`, `backend/auth.py`, `backend/test_app.py`, `backend/test_auth.py` |
| [#5](https://github.com/Data-Fellows/data-fellows-studio/pull/5) | #4 | `67da66b6` | Connect synthetic portal actions to authorized API | Hold · `.github/workflows/verify.yml`, `backend/app.py`, `backend/auth.py`, `backend/test_app.py`, `backend/test_auth.py`, `frontend/app.js`, `frontend/index.html`, `frontend/styles.css` |
| [#6](https://github.com/Data-Fellows/data-fellows-studio/pull/6) | #2 | `a22a1a54` | Route core API records through PostgreSQL | On #48 ancestry |
| [#7](https://github.com/Data-Fellows/data-fellows-studio/pull/7) | #6 | `5a00513f` | Add durable AI execution controls | On #48 ancestry |
| [#8](https://github.com/Data-Fellows/data-fellows-studio/pull/8) | #7 | `d2e52f30` | Run PostgreSQL integration tests in CI | On #48 ancestry |
| [#9](https://github.com/Data-Fellows/data-fellows-studio/pull/9) | #8 | `d43f0bff` | Harden professional admission authorization | On #48 ancestry |
| [#10](https://github.com/Data-Fellows/data-fellows-studio/pull/10) | #9 | `3bbeaec0` | Add scoped project and deliverable reads | On #48 ancestry |
| [#11](https://github.com/Data-Fellows/data-fellows-studio/pull/11) | #10 | `742cc252` | Connect synthetic Studio portal workspace | On #48 ancestry |
| [#12](https://github.com/Data-Fellows/data-fellows-studio/pull/12) | #11 | `73582dbe` | Add connected portal deliverable actions | On #48 ancestry |
| [#13](https://github.com/Data-Fellows/data-fellows-studio/pull/13) | #12 | `6304806e` | Complete scoped assignment lifecycle | On #48 ancestry |
| [#14](https://github.com/Data-Fellows/data-fellows-studio/pull/14) | #13 | `ac5f51fa` | Enforce immutable deliverable revisions | On #48 ancestry |
| [#15](https://github.com/Data-Fellows/data-fellows-studio/pull/15) | #14 | `659602c2` | Integrate Entra authentication with persistent stack | On #48 ancestry |
| [#16](https://github.com/Data-Fellows/data-fellows-studio/pull/16) | #15 | `4262968a` | Add scoped AI run status reads | On #48 ancestry |
| [#17](https://github.com/Data-Fellows/data-fellows-studio/pull/17) | #16 | `8184807f` | Persist work package dependencies | On #48 ancestry |
| [#18](https://github.com/Data-Fellows/data-fellows-studio/pull/18) | #17 | `bf759a3f` | Verify migration checksums | On #48 ancestry |
| [#19](https://github.com/Data-Fellows/data-fellows-studio/pull/19) | #18 | `0805037f` | Connect AI planning review workflow | Hold · `frontend/app.js`, `frontend/index.html` |
| [#20](https://github.com/Data-Fellows/data-fellows-studio/pull/20) | #18 | `f61b403d` | Test migration checksum tampering | On #48 ancestry |
| [#21](https://github.com/Data-Fellows/data-fellows-studio/pull/21) | #20 | `eb0ea54b` | Add scoped organization reads | On #48 ancestry |
| [#22](https://github.com/Data-Fellows/data-fellows-studio/pull/22) | #21 | `9778db5f` | Align client acceptance authorization | On #48 ancestry |
| [#23](https://github.com/Data-Fellows/data-fellows-studio/pull/23) | #22 | `656ead1b` | Add owner-scoped membership reads | On #48 ancestry |
| [#24](https://github.com/Data-Fellows/data-fellows-studio/pull/24) | #23 | `bcf362fc` | Expose authorized membership roster in admin portal | On #48 ancestry |
| [#25](https://github.com/Data-Fellows/data-fellows-studio/pull/25) | #24 | `eb6d2c10` | Connect professional assignment actions to portal | On #48 ancestry |
| [#26](https://github.com/Data-Fellows/data-fellows-studio/pull/26) | #25 | `4a7a5e7a` | Connect professional admission actions to portal | On #48 ancestry |
| [#27](https://github.com/Data-Fellows/data-fellows-studio/pull/27) | #26 | `4451de53` | Connect admin project setup actions to portal | On #48 ancestry |
| [#28](https://github.com/Data-Fellows/data-fellows-studio/pull/28) | #27 | `9e2a37c4` | Add admin professional admission queue | On #48 ancestry |
| [#29](https://github.com/Data-Fellows/data-fellows-studio/pull/29) | #28 | `e127937c` | Add admin membership revocation control | On #48 ancestry |
| [#30](https://github.com/Data-Fellows/data-fellows-studio/pull/30) | #29 | `e6cd4117` | Connect review and project completion actions | On #48 ancestry |
| [#31](https://github.com/Data-Fellows/data-fellows-studio/pull/31) | #30 | `43a83d4a` | Correct portal record status labels | On #48 ancestry |
| [#32](https://github.com/Data-Fellows/data-fellows-studio/pull/32) | #31 | `dd29d215` | Add fail-closed staging readiness checks | On #48 ancestry |
| [#33](https://github.com/Data-Fellows/data-fellows-studio/pull/33) | #32 | `965cee9c` | Harden Studio container packaging | On #48 ancestry |
| [#34](https://github.com/Data-Fellows/data-fellows-studio/pull/34) | #33 | `a5609831` | Document Studio staging release handoff | On #48 ancestry |
| [#35](https://github.com/Data-Fellows/data-fellows-studio/pull/35) | #34 | `f00e62ae` | Validate container definitions in CI | On #48 ancestry |
| [#36](https://github.com/Data-Fellows/data-fellows-studio/pull/36) | #35 | `a91b1565` | Add redacted secret scanning to Studio CI | On #48 ancestry |
| [#37](https://github.com/Data-Fellows/data-fellows-studio/pull/37) | #36 | `b914a79b` | Fix loopback frontend CORS preflight | On #48 ancestry |
| [#38](https://github.com/Data-Fellows/data-fellows-studio/pull/38) | #37 | `b79c124b` | Add Playwright lifecycle coverage and fix project selector | On #48 ancestry |
| [#39](https://github.com/Data-Fellows/data-fellows-studio/pull/39) | #38 | `7f412e0d` | Build polished professional portal workspace | On #48 ancestry |
| [#40](https://github.com/Data-Fellows/data-fellows-studio/pull/40) | #39 | `42aa905b` | Add Admin Mission Control | On #48 ancestry |
| [#41](https://github.com/Data-Fellows/data-fellows-studio/pull/41) | #40 | `7de3bc26` | Refine Admin Mission Control design workflow | On #48 ancestry |
| [#42](https://github.com/Data-Fellows/data-fellows-studio/pull/42) | #41 | `cb117fae` | Add secure client portal workflow | On #48 ancestry |
| [#43](https://github.com/Data-Fellows/data-fellows-studio/pull/43) | #42 | `43eaf52b` | Add scoped project collaboration slices | On #48 ancestry |
| [#44](https://github.com/Data-Fellows/data-fellows-studio/pull/44) | #43 | `89ae9a49` | Reuse legacy profile patterns in secure Studio onboarding | On #48 ancestry |
| [#45](https://github.com/Data-Fellows/data-fellows-studio/pull/45) | #44 | `328d4694` | Complete professional profile and admission review | On #48 ancestry |
| [#46](https://github.com/Data-Fellows/data-fellows-studio/pull/46) | #45 | `114e41e6` | Enforce independent admission review across storage modes | On #48 ancestry |
| [#47](https://github.com/Data-Fellows/data-fellows-studio/pull/47) | #46 | `9f599197` | Build the role-aware Studio workspace and verified delivery journeys | On #48 ancestry |
| [#48](https://github.com/Data-Fellows/data-fellows-studio/pull/48) | #47 | `df96b706` | Review scoped deliverable versions and corrections without entering IDs | On #48 ancestry |
| [#49](https://github.com/Data-Fellows/data-fellows-studio/pull/49) | #48 | `ae5c13bd` | Preserve admission history and revoke scoped project access | Release increment |
| [#50](https://github.com/Data-Fellows/data-fellows-studio/pull/50) | #49 | `7aa91a7a` | Connect project conversations, requests and handovers to role workspaces | Release increment |
| [#51](https://github.com/Data-Fellows/data-fellows-studio/pull/51) | #50 | `48856650` | Prepare delegated Entra web sessions for isolated staging | Release increment |
| [#52](https://github.com/Data-Fellows/data-fellows-studio/pull/52) | #51 | `e86e23ea` | Prepare protected Studio staging builds, migrations, verification and rollback | Release increment |
| [#53](https://github.com/Data-Fellows/data-fellows-studio/pull/53) | #52 | `14a7d24a` | Bind evidence verification to independent versioned admission decisions | Release increment |

## Migration and contract checks

Across the 53 inspected heads each numbered migration path below had one Git blob wherever present. No reused numeric prefix or modified historical migration body was found. Migrate the candidate in order in a disposable database first. New local runs used PostgreSQL 16 and validated replay and changed-checksum rejection.

| File | Unique Git blob |
|---|---|
| `migrations/001_initial.sql` | `e5e8d0e3c5e4` |
| `migrations/002_ai_execution_controls.sql` | `396db71d78e1` |
| `migrations/003_work_package_dependencies.sql` | `b7f529b8bdae` |
| `migrations/004_professional_opportunities.sql` | `718f588f0eda` |
| `migrations/005_client_revision_requests.sql` | `cc158b060555` |
| `migrations/006_project_operations.sql` | `0055e1b00b44` |
| `migrations/007_professional_profiles.sql` | `7bdd01714609` |
| `migrations/008_professional_admission_review.sql` | `9e4b5578eb19` |
| `migrations/009_release_access.sql` | `82f04d038c96` |
| `migrations/010_project_coordination.sql` | `5116173f9908` |

The retired admission endpoints return 410. Replaying an application after staff review returns 409. Qualification policy v2 requires a reviewed profile version and verified evidence selections. Revisions remain new deliverable versions. External project activity returns project lifecycle events and timestamps. Conversation records carry the messages separately. External clients relying on raw audit metadata, resubmission resets, unscoped assignments or legacy approval must update before cutover.

New completion creates an accepted-version handover manifest in the same transaction. A historical completion without a manifest remains unrecorded. Existing commercial records, compensation and inaccessible documents are outside this change.

The previous identity matrix described resubmission and compatibility approval incorrectly. The current identity, policy and deployment documents supersede that wording. Older UI reports and migration counts are dated historical evidence. Open coverage gaps include real tenant login, session revocation, private dependencies, cost entitlements, restore, live RBAC and actual revision traffic rollback.
