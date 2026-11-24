-- Data Fellows Studio initial relational model.
-- Application code supplies UUIDs; PostgreSQL remains the source of truth.

CREATE TABLE IF NOT EXISTS organizations (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (length(trim(name)) >= 2),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memberships (
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id text NOT NULL CHECK (length(trim(actor_id)) >= 2),
    role text NOT NULL CHECK (role IN ('client', 'professional', 'reviewer', 'owner')),
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    PRIMARY KEY (organization_id, actor_id, role),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);

CREATE INDEX IF NOT EXISTS memberships_actor_active_idx
    ON memberships(actor_id, organization_id) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS professional_admissions (
    professional_id text PRIMARY KEY CHECK (length(trim(professional_id)) >= 2),
    status text NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'revoked')),
    decided_by text,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engagements (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(trim(name)) >= 2),
    objective text NOT NULL CHECK (length(trim(objective)) >= 2),
    status text NOT NULL CHECK (status IN ('authorized', 'active', 'completed', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS engagements_organization_idx ON engagements(organization_id, created_at);

CREATE TABLE IF NOT EXISTS projects (
    id uuid PRIMARY KEY,
    engagement_id uuid NOT NULL REFERENCES engagements(id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(trim(name)) >= 2),
    status text NOT NULL CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS work_packages (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    title text NOT NULL CHECK (length(trim(title)) >= 2),
    acceptance_criteria jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('unassigned', 'assigned', 'in_progress', 'under_review', 'completed')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assignments (
    id uuid PRIMARY KEY,
    work_package_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    professional_id text NOT NULL REFERENCES professional_admissions(professional_id) ON DELETE RESTRICT,
    status text NOT NULL CHECK (status IN ('invited', 'accepted', 'declined', 'expired', 'revoked')),
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS active_assignment_idx
    ON assignments(work_package_id, professional_id) WHERE status IN ('invited', 'accepted');

CREATE TABLE IF NOT EXISTS ai_runs (
    id uuid PRIMARY KEY,
    work_package_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    requested_by text NOT NULL,
    agent_version text NOT NULL,
    policy_version text NOT NULL,
    budget_cents integer NOT NULL CHECK (budget_cents > 0),
    spent_cents integer NOT NULL DEFAULT 0 CHECK (spent_cents >= 0 AND spent_cents <= budget_cents),
    status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS artifacts (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES ai_runs(id) ON DELETE RESTRICT,
    version integer NOT NULL CHECK (version > 0),
    content jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('pending_review', 'approved', 'rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, version)
);

CREATE TABLE IF NOT EXISTS deliverables (
    id uuid PRIMARY KEY,
    work_package_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    version integer NOT NULL CHECK (version > 0),
    title text NOT NULL CHECK (length(trim(title)) >= 2),
    content text NOT NULL CHECK (length(trim(content)) >= 2),
    submitted_by text NOT NULL,
    status text NOT NULL CHECK (status IN ('under_review', 'revision_requested', 'approved', 'accepted')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (work_package_id, version)
);

CREATE TABLE IF NOT EXISTS deliverable_reviews (
    id uuid PRIMARY KEY,
    deliverable_id uuid NOT NULL REFERENCES deliverables(id) ON DELETE RESTRICT,
    reviewer_id text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('approved', 'revision_requested')),
    comment text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id uuid PRIMARY KEY,
    organization_id uuid REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id text NOT NULL,
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_events_organization_idx ON audit_events(organization_id, created_at);
