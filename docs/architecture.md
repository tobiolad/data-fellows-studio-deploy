# Studio foundation architecture

The first slice is a modular API with organization-scoped delivery records. The current repository uses an in-memory repository so synthetic tests are deterministic; PostgreSQL is the required next persistence adapter before any real data.

## Boundaries

- Clients see only their organization's engagements, approved updates and accepted deliverables.
- Internal admins own commercial and delivery actions.
- Approved professionals receive assignment-scoped access only.
- Reviewers independently approve AI artifacts and deliverables.
- AI runs are service records, not human memberships, and cannot grant permissions.

## Identity

Production identity will use separate Entra audiences for Studio clients, staff and service identities. The current `Bearer test:` adapter is accepted only when `STUDIO_TEST_MODE=true`; the default rejects all requests with a clear Entra configuration response.

## Persistence migration

The in-memory `Store` maps directly to organizations, memberships, engagements, projects, work packages, assignments, AI runs, artifacts, deliverables, reviews and audit events. The PostgreSQL adapter must preserve organization IDs, unique membership/assignment constraints, immutable artifact versions and append-only audit events.
