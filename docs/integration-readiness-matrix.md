# Studio integration readiness matrix

Evidence basis: current branch codex/platform-vertical-slices, local PostgreSQL-backed
tests, Playwright synthetic runs and the read-only Azure workflow definition. No
live Azure deployment or Entra sign-in has been executed.

| Capability | Status | Evidence / remaining gate |
| --- | --- | --- |
| Admin Portal | Implemented and tested | Mission Control Playwright smoke and API authorization tests pass. |
| Professional Portal | Implemented and tested | Assignment, opportunity, deliverable and review flows pass synthetic walkthrough. |
| Professional profile and onboarding | Implemented in focused reuse increment | `professional_profiles` migration, own/admin API, version checks, audit event, and synthetic Playwright evidence. Add admin evidence review and private scanner-backed uploads before real applications. |
| Client Portal | Implemented and tested | Approved-only deliverables, revision/acceptance, mobile screenshot and project messaging pass. |
| AI orchestration | Implemented and tested (synthetic) | Deterministic bounded planner and independent approval pass; live provider disabled. |
| Database | Implemented and tested | Versioned migrations 001-007, transaction repository and PostgreSQL integration pass when the configured test database is available. |
| Authorization | Implemented and tested locally | Cross-organization, revoked-access and self-approval negatives pass; Entra validation remains external. |
| BizPilot integration | Partially implemented | Handoff contracts exist in BizPilot; live Studio receiver and service identity are not connected. |
| HubSpot | Not implemented | Keep CRM authoritative; add an approved adapter only when credentials and scope are approved. |
| Stripe | Not implemented | No live payment processing or payout flow is enabled. |
| Messaging | Implemented and tested | Project-scoped client/internal and professional/supervisor API; client UI composer and activity view pass. |
| Documents | Partially implemented | Secure metadata/reference records exist; private Blob upload/download and malware scan remain staging gates. |
| Support | Partially implemented | Client-safe empty state exists; support agreements/ticket persistence remain. |
| Azure staging | Partially implemented | OIDC read-only preflight workflow and runbook are ready; no resources were provisioned. |
| Entra authentication | Partially implemented | Configurable JWT validator exists; tenant registrations and two test identities remain. |
| Monitoring | Not implemented | Add approved Log Analytics/Application Insights wiring during staging. |
| Security | Implemented and tested locally | Backend scope checks, audit records, safe reference handling and secret scan CI pass. |
| Production readiness | Blocked | Requires live identity, private data services, backups/restore, network probes and authenticated browser verification. |

## Dependency order

Merge the existing stack through PR #42, then review this focused vertical-slice
branch. Run migration 006 after 005. Keep the Azure preflight workflow read-only
until the owner protects the deployment environments and approves a what-if.

## Owner gates

- Configure Entra API/SPA registrations and analyst/reviewer identities.
- Approve PostgreSQL, private Blob, Key Vault, queue, private endpoints, monitoring and cost controls.
- Run the OIDC preflight from the protected GitHub environment.
- Approve a staging what-if, migration run and synthetic post-deployment verification.
