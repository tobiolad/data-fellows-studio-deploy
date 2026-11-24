# Studio screen reference library

This is the implementation reference for the three Studio portals. It intentionally describes contracts and states instead of copying third-party branding. The current visual baseline is the committed Studio Playwright evidence in `artifacts/` and the Data Fellows screenshots supplied to the team.

## Shared rules

- Use the existing navy sidebar, royal-blue action, white panel and soft-gray canvas tokens.
- Every screen has loading, empty, error and unauthorized states. Counts come from API records; unavailable money is labelled unavailable.
- Human-readable names are displayed; UUIDs are hidden behind links and selectors.
- Keyboard focus is visible, tables collapse to cards at 680px, and status text is not conveyed by color alone.

## Admin Mission Control

| Screen | Purpose / user | Layout and components | Primary actions / data | Mobile and accessibility |
|---|---|---|---|---|
| Overview | Internal admin/reviewer | Summary cards, delivery pipeline, attention queue, recent projects, AI queue | `GET /api/admin/overview`; open project/application/run details | Stack pipeline and queues; table becomes labelled cards; actions have text labels |
| CRM & engagements | Admin/relationship owner | Searchable engagement table and detail drawer | `GET /api/engagements`, `POST /api/engagements`; create authorized engagement | Filter by status; announce result/error |
| Clients | Admin | Organization list/detail | `GET /api/organizations`; membership-scoped detail | No client-only internals |
| Projects & delivery | Admin/delivery owner | Project table → project/work-package detail | project and work-package endpoints; status transitions | Avoid manual IDs; focus returns after drawer |
| Applications & vetting | Admin | Application queue with evidence, status and decision history | `GET /api/professionals/admissions`, decision endpoint | Confirm before decision; reviewer identity visible |
| Opportunities & staffing | Admin | Sanitized opportunity table, interest review, invitation drawer | opportunity and interest endpoints | Never reveal client identity or private scope |
| AI Operations | Admin/security admin | Registry, approval queue, running/failed history, artifact detail | AI run/artifact endpoints | Synthetic executor label and budget shown |
| Quality review | Independent reviewer | Deliverable/version review queue | review endpoint; immutable version detail | Self-review rejected server-side |
| Client approvals | Admin | Presented versions and decision history | client acceptance/revision records | Client identity required for acceptance |
| Communications | Internal | Project-scoped channels and activity | project messages/activity endpoints | No direct client-professional channel |
| Finance | Finance role | Verified invoices, payment events and payables | future HubSpot/Stripe contracts; synthetic records only | Hide from non-finance roles |
| Security & audit | Security/admin | Filterable audit timeline | audit records | Export safe metadata only |

## Professional Portal

| Screen | Purpose / user | Components and actions |
|---|---|---|
| Overview | Approved professional | Assignment summary, invitations, review feedback; API-backed only |
| My applications | Applicant/professional | Admission status, opportunity expressions of interest, evidence checklist; submit/withdraw within policy |
| Profile | Applicant/professional | Structured editable profile: identity, headline, bio, skills, specializations, education, experience, portfolio references, availability; save draft without approval |
| Opportunities | Approved professional | Sanitized searchable opportunity cards, eligibility and express-interest form |
| Assignments | Approved professional | Human-readable project/work-package cards; scoped detail and status updates |
| Invitations | Approved professional | Terms, deadline, acceptance criteria, confidentiality and accept/decline |
| Deliverables | Assigned professional | Versioned submission and revision history; no approval controls |
| Reviews & feedback | Assigned professional | Reviewer comments and decisions on their versions |
| Messages | Assigned professional | Supervisor-only project channel |
| Earnings | Approved professional | Verified compensation/payables only; no fabricated totals |

## Client Portal

| Screen | Purpose / user | Components and actions |
|---|---|---|
| Overview | Authorized client member | Active/completed project counts, attention queue, approved outcomes |
| Projects & engagements | Client member | Searchable project records, milestones and status; no staffing controls |
| Deliverables | Client member | Internally approved versions, source context, accept/request revision |
| Documents | Client member | Authorized metadata and private download references when storage is configured |
| Messages | Client member | Project-scoped Data Fellows channel and activity timeline |
| Billing | Authorized finance contact | Verified invoice/payment events; unavailable until integration is connected |
| Support | Contracted client | Support agreement, requests, incidents and outcome measurements |

## Visual references and provenance

The supplied Professional Portal and Mission Control screenshots define hierarchy, spacing and color intent. Linear/Attio/Notion/Intercom/Deel were considered pattern references only; no proprietary assets or code are copied. Legacy source references are listed in `LEGACY_COMPONENT_INVENTORY.md`.
