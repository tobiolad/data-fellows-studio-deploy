# Admin Mission Control

Mission Control is the internal admin surface for Data Fellows Studio. It is
available only to an identity with the backend `admin` role; the UI visibility
is not an authorization boundary.

## Current increment

- `/api/admin/overview` returns a read-only PostgreSQL (or synthetic-memory)
  operational read model for organizations, engagements, projects,
  professional admission, opportunities, deliverables, bounded AI runs and
  recent audit events.
- Counts are derived from persisted records. Missing finance, support and
  product records render as explicit empty states rather than invented metrics.
- Mission Control routes cover the operational navigation: delivery, clients,
  professional network, vetting, staffing, AI operations, quality, approvals,
  audit and platform settings.
- The synthetic developer harness remains available for local lifecycle tests;
  it is not a production authentication mechanism.

## Authorization

The API calls `require_global(actor, "admin")` before returning the read model.
Professional, client and reviewer identities receive `403`. Entra-backed
deployment must map internal admin permissions to the server-side role model;
frontend route visibility must never be treated as sufficient protection.

## Verification

`tests/playwright/admin-mission-control.js` exercises the admin navigation at
desktop and mobile sizes, checks the admin denial path, and records console and
request failures. It uses synthetic identities and the local PostgreSQL test
database only.
