# Legacy component inventory

Audit date: 2026-11-21. This inventory records source that was actually inspected. The archived repositories are private and have no declared SPDX license in GitHub metadata; reuse therefore assumes Data Fellows ownership/contractual clearance, not an open-source license.

## Repositories and verified status

| Repository | Status / stack | Evidence inspected | Security and compatibility conclusion |
|---|---|---|---|
| `Data-Fellows/data-fellows-core-web-client` | Archived, private; Next.js 15.3.1, React 18, TypeScript, React Hook Form/Zod, Radix, TanStack Query, Zustand, country-state-city, Tiptap, OpenAI | `src/app/employer/(onboarding)/onboarding/_components/index.tsx`, `step-one.tsx`–`step-five.tsx`, `use-onboarding-form-store.ts`, `FileDropZone.tsx`, `ImportCVForm.tsx`; employer profile components and dashboard | Adapt interaction patterns only. It is a marketplace UI with client-side state and external Affinda/OpenAI calls; do not copy auth, payment, matching or file-upload code. |
| `Data-Fellows/data-fellows-core-backend-service` | Archived, private; Express/TypeScript, MongoDB/Mongoose, Passport, AWS S3, OpenAI, Stripe | `src/controllers/profile.ts`, `src/routes/profile.ts`, `src/models/User.ts`, `src/services/upload-image.ts`, `src/services/cv-parser.ts`, `src/controllers/message.ts`, `src/models/{Milestone,Payment,Payout}.ts` | Reference only. Public registration accepts `userType`, profile writes are broad, S3 URLs are returned, CV text is sent to OpenAI, and marketplace/match authorization is not a Studio boundary. |
| `Data-Fellows/data-fellows-frontend-clean` | Archived, private; Next.js app; same onboarding/profile family | GitHub tree confirms auth, employer onboarding/profile, user onboarding and settings paths | Adapt visual/form patterns after review; do not import dependencies or auth wholesale. |
| `Data-Fellows/data-fellow-frontend` | Archived, private; Next.js app | `src/app/user/(onboarding)/onboarding/_components/step-one.tsx` through `step-eight.tsx`; `src/app/user/(user)/profile/_components/{edit-profile,education-history,work-experience}.tsx`; dashboard stats | Best evidence for the eight-step profile flow and editable sections. Adapt field semantics and progress language; replace role model, persistence and authorization. |
| `Data-Fellows/data-fellows-FE` | Archived, private; legacy React/Next source with checked-in dependency tree | `src/auth/{signin,signup}`, `src/components` | Reference only until a file-by-file license and dependency review is completed. No direct copy. |
| `Data-Fellows/data-fellows-web-app` | Active, public; Next.js + Supabase; public website/CMS | `src/layouts/{landing-page,index,admin-layout}.tsx`, `src/pages/*`, `supabase/migrations/*`; public assets include product screenshots | Preserve boundary. Reuse brand tokens or public copy only where approved; never connect Studio to website `/admin` membership or CMS data. |
| `Data-Fellows/bizpilot-pro-concept` | Active, private; Next.js/FastAPI/PostgreSQL/Pandas | `backend/diagnostics/*`, `frontend/src/components/{DiagnosticWorkspace,ResearchPanel,PricingPanel}.tsx`, `docs/architecture/studio-integration.md` | Keep separate. Reuse only the versioned, approved handoff contract concept; do not share client datasets or identity boundary. |

## Capability map

| Capability | Verified implementation | Reuse recommendation |
|---|---|---|
| Professional onboarding | `data-fellow-frontend` `step-one.tsx`–`step-eight.tsx`: intro, role/speciality, skills, experience, education, bio, personal details, completion | Adapt copy and step sequencing into Studio; rebuild persistence and approval gates. |
| Professional profile | `data-fellow-frontend` profile `edit-profile.tsx`, `education-history.tsx`, `work-experience.tsx`; backend `profile.ts` and `User.ts` | Adapt component intent and field vocabulary. Do not copy Mongo model or broad update endpoint. |
| Skills/specializations | Legacy category/speciality and skills selectors (`step-two.tsx`, `step-three.tsx`) | Adapt as controlled lists; store in Studio profile record and never infer approval. |
| Education/experience | Legacy modal forms and CV import (`step-four.tsx`, `step-five.tsx`, `ImportCVForm.tsx`) | Adapt manual structured entry first. CV parsing is optional, quarantined and human-reviewed later. |
| Portfolio/documents | `FileDropZone.tsx`, profile photo upload, S3 helper | Redesign for private storage/quarantine; legacy returned public S3 URLs and lacked scanner boundary. |
| Company/client profile | Core web `employer/(onboarding)` `step-two.tsx`, `company-form.tsx`, `profile-details.tsx` | Adapt organization profile fields; keep HubSpot authoritative and Studio membership-scoped. |
| Authentication | Core web auth routes; backend Passport/JWT | Retire as production auth. Studio uses Entra validation and server roles; synthetic adapter remains test-only. |
| Dashboards | Legacy employer/user stats and listings; active website layouts | Reuse information grouping only. Studio dashboard metrics must come from authorized records. |
| Messaging | Backend `src/controllers/message.ts` and Match model | Reject direct-match model. Studio uses project-scoped client↔Data Fellows and professional↔supervisor channels. |
| Milestones | `src/models/Milestone.ts` | Reference status vocabulary; rebuild around Studio projects/work packages and immutable approvals. |
| Payments | `src/models/Payment.ts`, `Payout.ts`, Stripe service | Reject Connect/payout flow. Preserve verified event boundary and separate professional payables. |
| Application tracking | Legacy job/application routes and user settings | Adapt statuses as admission/opportunity/assignment states; do not restore employer hiring marketplace. |

## Verified limitations

- No screenshot was captured from the archived Next.js apps in this environment: they require their original dependency/bootstrap and credentials, and their source is not a safe running reference. Current Studio screenshots are the authoritative visual baseline. This is recorded rather than presenting a fabricated legacy image.
- GitHub metadata reports no declared license for the private legacy repositories. Confirm contributor and contractual IP rights before extracting code.
- The backend has no automated test script (`test` exits with an error), so source behavior is evidence, not a production-readiness claim.
