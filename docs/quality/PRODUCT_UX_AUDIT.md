# Studio UX audit

Baseline is PR #45 at `328d469`. Screenshots use the same synthetic PostgreSQL database for the parent and implementation. The 1440px images show the initial viewport. Interaction findings also use the route markup in `frontend/index.html`, handlers in `frontend/app.js` and the API read models.

The mobile baseline put a truncated scrolling navigation strip above a second menu button. The button operated on the first navigation list for every identity. The desktop top bar included a search field with no handler and a notification indicator without an event source.

## Admin

| Screen | Baseline finding | Browser evidence |
|---|---|---|
| Mission Control | The New engagement action had no handler. Approved admissions were labeled available and artifact review was labeled run authorization. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-overview-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-overview-1440.png) |
| CRM and engagements | One card per engagement with no collection controls. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-engagements-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-engagements-1440.png) |
| Clients | Organization cards provide little operating context. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-clients-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-clients-1440.png) |
| Projects and delivery | Project detail exposes a generic property list. Cards are paged but dependencies and handover are disconnected. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-projects-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-projects-1440.png) |
| Professional network | Subject identifiers serve as titles. Approved and available are different states. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-professionals-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-professionals-1440.png) |
| Applications and vetting | Queue titles use actor identifiers and repeated cards. Approval could proceed without qualifications or references. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-applications-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-applications-1440.png) |
| Opportunities and staffing | Published opportunities are readable but selection and invitation are separate operations. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-opportunities-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-opportunities-1440.png) |
| AI operations | Artifact decisions, execution states and spend are easy to conflate. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-ai-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-ai-1440.png) |
| Quality review | List emphasizes status. Version comparison and reviewer reasoning are hard to inspect together. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-quality-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-quality-1440.png) |
| Client approvals | Overview of review status lacks the context of acceptance criteria and version lineage. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-approvals-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-approvals-1440.png) |
| Communications | Static empty state despite a project message API. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-communications-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-communications-1440.png) |
| Finance | Empty state describes future verified records. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-finance-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-finance-1440.png) |
| Managed operations | Placeholder lacks a contracted support queue. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-operations-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-operations-1440.png) |
| Product portfolio | Placeholder has no actionable portfolio. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-products-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-products-1440.png) |
| Security and audit | Raw event keys and resource IDs dominate the list. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-audit-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-audit-1440.png) |
| Settings | Static configuration descriptions cannot verify deployment health. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/admin-admin-settings-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/admin-admin-settings-1440.png) |

## Professional

| Screen | Baseline finding | Browser evidence |
|---|---|---|
| Assignment overview | Dashboard inferred review availability from accepted work and showed invitations in the active-work table. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-overview-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-overview-1440.png) |
| My applications | Unapproved applicants saw delivery navigation. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-applications-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-applications-1440.png) |
| Professional profile | The evidence editor and its host used different IDs. An empty profile could retain another synthetic identity’s optimistic version. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-profile-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-profile-1440.png) |
| Available opportunities | Applicant navigation exposed a route the API would deny. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-opportunities-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-opportunities-1440.png) |
| My assignments | Listing inherited the dashboard preview limit and mixed statuses. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-assignments-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-assignments-1440.png) |
| Invitations | Pending invitations were also surfaced as active work. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-invitations-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-invitations-1440.png) |
| Deliverables | A professional had to select or type a package identifier. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-deliverables-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-deliverables-1440.png) |
| Reviews and feedback | Static feedback message does not load the recorded review history. Reviewer mode also shared all professional routes. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-reviews-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-reviews-1440.png) |
| Messages | Static empty state with no assigned-project thread. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-messages-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-messages-1440.png) |
| Earnings and payments | No verified compensation source exists on this screen. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-earnings-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-earnings-1440.png) |
| Help and support | Static help text does not create or track a case. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/professional-help-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/professional-help-1440.png) |

## Client

| Screen | Baseline finding | Browser evidence |
|---|---|---|
| Client overview | Client header reused an unrelated professional avatar and an inert global search. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-overview-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-overview-1440.png) |
| Projects and engagements | Project cards show summaries but scope, milestones and decisions are disconnected. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-projects-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-projects-1440.png) |
| Deliverable review | Acceptance and revision actions exist but the screen has limited version-comparison context. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-deliverables-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-deliverables-1440.png) |
| Project messages | Project-scoped messages exist alongside separate project and deliverable pages. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-communications-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-communications-1440.png) |
| Billing | No verified invoices or payments can be displayed. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-billing-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-billing-1440.png) |
| Support | Contract-aware incident creation and status are unavailable. | [Before](BEFORE_AND_AFTER_SCREENSHOTS/before/client-client-support-1440.png) · [After](BEFORE_AND_AFTER_SCREENSHOTS/after/client-client-support-1440.png) |

## Independent review

Impeccable static and rendered results are retained in PLAYWRIGHT_RESULTS. Browser layout checks cover route selection, viewport width and keyboard disclosure. Manual screen-reader, cognitive walkthrough and sustained-load evaluation remain outstanding.
