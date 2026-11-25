-- A client's organization-level question for Data Fellows, not tied to any
-- one project -- distinct from project_messages, which always needs one.
CREATE TABLE IF NOT EXISTS support_requests (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    submitted_by text NOT NULL CHECK (length(trim(submitted_by)) >= 2),
    subject text NOT NULL CHECK (length(trim(subject)) BETWEEN 2 AND 200),
    body text NOT NULL CHECK (length(trim(body)) BETWEEN 2 AND 4000),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    resolved_by text,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);

CREATE INDEX IF NOT EXISTS support_requests_organization_idx
    ON support_requests(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS support_requests_status_idx
    ON support_requests(status, created_at);
