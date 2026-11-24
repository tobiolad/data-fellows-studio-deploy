# Studio foundation architecture

The first slice is a modular API with organization-scoped delivery records. Synthetic tests retain an in-memory adapter for deterministic local execution; the PostgreSQL repository and migration set establish the production persistence boundary before any real data.

## Boundaries

- Clients see only their organization's engagements, approved updates and accepted deliverables.
- Internal admins own commercial and delivery actions.
- Approved professionals receive assignment-scoped access only.
- Reviewers independently approve AI artifacts and deliverables.
- AI runs are service records, not human memberships, and cannot grant permissions.

## Identity

Production identity will use separate Entra audiences for Studio clients, staff and service identities. The current `Bearer test:` adapter is accepted only when `STUDIO_TEST_MODE=true`; the default rejects all requests with a clear Entra configuration response.

## Persistence boundary

The in-memory `Store` maps directly to organizations, memberships, engagements, projects, work packages, assignments, AI runs, artifacts, deliverables, reviews and audit events. `backend/persistence.py` provides transaction-safe PostgreSQL primitives for organizations, memberships and audit reads, with the remaining domain writes following the same repository boundary. The schema preserves organization IDs, unique membership/assignment constraints, immutable artifact versions and append-only audit events.

Run migrations through `PostgresRepository.migrate()` from an approval-controlled migration job. The API must not auto-create or alter production schema during request handling. PostgreSQL integration tests run only when `STUDIO_TEST_DATABASE_URL` points to an approved synthetic database.
