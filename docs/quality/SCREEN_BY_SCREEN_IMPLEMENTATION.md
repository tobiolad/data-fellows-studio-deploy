# Screen-by-screen implementation

Status describes the complete requested screen. The shared navigation gate covers all 33 route IDs and the reviewer variant. Individual workflow coverage varies.

## Admin

| Screen | Status | Implementation and outstanding work | Authoritative dependency |
|---|---|---|---|
| Mission Control | In development | Wired organization-backed creation and destinations for four corrected metrics. Risk, commercial ownership and deadlines need recorded fields. | Admin overview, organizations, engagements |
| CRM and engagements | In development | Added searchable, sortable, paginated rows and a detail action. Ownership and next-action fields are outstanding. | Engagement and organization read models |
| Clients | In development | Shared shell upgraded. Organization onboarding and member detail still need work. | Organization memberships |
| Projects and delivery | In development | Preserved existing search and pagination. Improved keyboard containment in detail drawers. | Project, work-package and dependency records |
| Professional network | In development | Read models now join display names when available. Availability and assignment capacity still need separate presentation. | Admission and profile records |
| Applications and vetting | In development | Added searchable queue, human labels, structured qualification summary, evidence references and version-bound review. Assessment resolution history needs more work. | Admission, profile version, evidence metadata and audit |
| Opportunities and staffing | In development | Shell upgraded. Formal agreements and an integrated selection journey remain outstanding. | Sanitized opportunities, interests, assignments |
| AI operations | In development | Dashboard labels output review explicitly. Registry, policy, intervention and evaluation workspaces remain incomplete. | Runs, artifacts, policy and cost records |
| Quality review | In development | Shell upgraded. Independent reviewer inspection still needs a scoped queue and version comparison. | Deliverables, internal review and assignment scope |
| Client approvals | In development | Shell upgraded. Client decisions are exercised through the client workflow. | Deliverables and version decisions |
| Communications | Not implemented | Admin inbox and authorized threads need implementation. | Project-scoped messages |
| Finance | Blocked | Verified ledger integration remains blocked. | Verified invoice and payment events |
| Managed operations | Not implemented | Contract and incident workflows remain outstanding. | Contract entitlement and ticket records |
| Product portfolio | Not implemented | Needs a defined operational source or removal from routine navigation. | Product and ownership records |
| Security and audit | In development | Searchable recent events, readable titles, date sorting, pagination and expandable technical details. Full history and indexed server filters remain outstanding. | Recent admin audit snapshot |
| Settings | In development | Shell upgraded. Live configuration evidence still belongs to staging validation. | Readiness endpoint and infrastructure evidence |

## Professional

| Screen | Status | Implementation and outstanding work | Authoritative dependency |
|---|---|---|---|
| Assignment overview | In development | Shows accepted work separately from invitations and labels access expirations. A verified review queue remains outstanding. | Own assignments and professional admission |
| My applications | In development | Applicant navigation now limits routes to applications, profile and help. The backend currently requires an application before profile creation. | Own admission record |
| Professional profile | In development | Repaired evidence editing and draft loading. Preserved structured rows and optimistic saves. Credential verification remains outstanding. | Own structured profile and version |
| Available opportunities | In development | Shows only after recorded approval. Existing interest submission still uses a browser prompt. | Published eligible opportunities and interests |
| My assignments | In development | All accepted assignments appear in the workspace and the overview previews five. Large collections still need pagination. | Own accepted assignments |
| Invitations | In development | Invitations stay separate from accepted work. Agreement objects remain outstanding. | Invited assignments |
| Deliverables | In development | Added a readable accepted-assignment selector and version-specific submission path. | Accepted assignments and deliverable versions |
| Reviews and feedback | In development | Reviewer navigation is scoped. A reviewer-specific queue and professional feedback history remain outstanding. | Independent review and deliverable history |
| Messages | Not implemented | Professional communications still need a scoped read and write surface. | Project channels and assignment authorization |
| Earnings and payments | Blocked | Continues to show unavailable financial data. | Verified compensation and payout records |
| Help and support | In development | Shell upgraded. Contract-aware support intake remains outstanding. | Support entitlement and ticket records |

## Client

| Screen | Status | Implementation and outstanding work | Authoritative dependency |
|---|---|---|---|
| Client overview | In development | Role-specific location and linked client metrics replace those shell elements. Relationship lead is still missing. | Client-scoped overview |
| Projects and engagements | In development | Shared navigation upgraded. A project-detail workspace remains outstanding. | Client-visible project records |
| Deliverable review | In development | Retained real version decisions. Existing walkthrough exercises revision, independent re-review and acceptance. | Client-safe reviewed deliverables |
| Project messages | In development | Preserved project scope. Thread organization and document context remain outstanding. | Project operations API |
| Billing | Blocked | Empty state retained. Verified billing integration is blocked. | Verified Stripe events |
| Support | Not implemented | Empty state retained. Support workflow remains outstanding. | Support entitlements and scoped tickets |

## Reviewer

The reviewer uses the reviews route with a restricted navigation list. A reviewer can record an independent decision in the synthetic lifecycle. A scoped review worklist with evidence, criteria, author and version comparison is in development.
