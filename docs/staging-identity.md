# Studio staging identity contract

Use one workforce tenant. Register business guests in that tenant. Keep Studio, BizPilot, CI jobs, the migration job and AI execution identities separate.

| Registration | Configuration |
|---|---|
| Studio Staging API | Single tenant. Set requestedAccessTokenVersion to 2. Set application ID URI to api://<API application ID>. Expose the delegated scope Studio.Access, admin consent only. Define User app roles with values admin, reviewer, client and professional. Require assignment on its enterprise application. Set STUDIO_ENTRA_AUDIENCE to the API application GUID from the v2 access token. |
| Studio Staging Web | Single tenant, confidential Web client for Container Apps built-in authentication. Register only https://<approved-studio-host>/.auth/login/aad/callback as the Web redirect URI. Authorize the API delegated scope, grant tenant admin consent, require enterprise application assignment. Disable implicit grants and public-client flows. Configure an owner-approved credential reference and rotation at the platform boundary. |
| Runtime | STUDIO_ENV=staging, STUDIO_TEST_MODE=false, STUDIO_ENTRA_ENABLED=true, STUDIO_PLATFORM_AUTH=easy-auth, STUDIO_PUBLIC_ORIGIN=https://<approved-studio-host>, STUDIO_ENTRA_TENANT_ID=<tenant GUID>, STUDIO_ENTRA_WEB_CLIENT_ID=<web application GUID>. Configure PostgreSQL separately. Use the tenant-specific issuer. |
| Container Apps ingress | Only the Studio web container receives external traffic. Run the API as a sidecar on loopback-accessible port 8100. Configure Microsoft provider on ingress, HTTPS only, protected endpoints return 401 to anonymous API requests. Permit anonymous static sign-in content and the approved health probe as appropriate. Configure provider login parameters to request openid, profile, offline_access and api://<API application ID>/Studio.Access. Enable the supported private token store and validate injection/renewal of X-MS-TOKEN-AAD-ACCESS-TOKEN. Restrict access to the platform token store. |

The browser uses a same-origin platform session. The proxy forwards requests to the API. The API checks the access token signature, issuer, audience, tenant, authorized web client, expiry, delegated scope, stable object ID and exactly one supported role. Cookie-based writes also require the configured public origin. Only the explicit local synthetic harness sends a test bearer token.

## Owner acceptance on the private staging host

Assign one Studio API role per account and grant the Web enterprise application separately. Map organization memberships to the tenant-local object IDs, including for B2B guests.

| Identity | Required live evidence |
|---|---|
| Staff owner, separate reviewer | Staff creates records. Independent reviewer sees only authorized submissions and cannot approve their own work. |
| Client A, client B in different organizations | Each can read and decide only in their own organization. Check a cross-organization denial, including project documents and notifications. |
| Applicant, approved professional | Applicant sees the admission flow. The professional accepts a scoped invitation, then loses work access after revocation. Regranting membership does not restore the old assignment. |
| Disabled user and workload principal | Check session expiry, Conditional Access and revoke-session timing. A workload principal cannot enter a human workspace. |

Verify sign-in, logout, expiry, consent failure, no bearer token in browser storage, API 401 instead of an HTML redirect and cross-origin write rejection. Capture redacted outcomes only. The staging owner must verify provider token forwarding on the actual Container Apps configuration. Subscription access, consent, application credentials, test accounts and token storage are outstanding.
