-- Studio receiver for the BizPilot diagnostic handoff contract
-- (see bizpilot-pro-concept docs/architecture/studio-integration.md).
--
-- A diagnostic_links row is the authorized-owner linkage step
-- ("Diagnostics.Link.Write: Idempotent Studio reference and authorized
-- owner" in that contract): a Studio owner/admin explicitly connects one
-- external BizPilot engagement to one Studio organization before any
-- handoff for it can be accepted. Nothing here creates a Studio
-- organization automatically -- that remains an owner/sales decision.
CREATE TABLE IF NOT EXISTS diagnostic_links (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    source_system text NOT NULL CHECK (source_system IN ('bizpilot')),
    source_engagement_id text NOT NULL CHECK (length(trim(source_engagement_id)) >= 2),
    linked_by text NOT NULL CHECK (length(trim(linked_by)) >= 2),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_system, source_engagement_id)
);

-- A diagnostic_handoffs row is the idempotent record of one accepted
-- handoff delivery ("Record Studio project or update linkage:
-- Diagnostics.Link.Write -- audited upsert with expected version"). The
-- (link_id, idempotency_key) pair lets a repeated delivery attempt return
-- the same created engagement/project instead of duplicating it.
CREATE TABLE IF NOT EXISTS diagnostic_handoffs (
    id uuid PRIMARY KEY,
    link_id uuid NOT NULL REFERENCES diagnostic_links(id) ON DELETE RESTRICT,
    idempotency_key text NOT NULL CHECK (length(trim(idempotency_key)) >= 8),
    source_report_id text NOT NULL CHECK (length(trim(source_report_id)) >= 2),
    source_report_version integer NOT NULL CHECK (source_report_version > 0),
    engagement_id uuid NOT NULL REFERENCES engagements(id) ON DELETE RESTRICT,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    received_by text NOT NULL CHECK (length(trim(received_by)) >= 2),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (link_id, idempotency_key)
);

-- Per-work-package provenance: the source recommendation id and sanitized
-- evidence references (citation ids/providers/urls only -- never raw
-- datasets, per the contract's explicit exclusion).
CREATE TABLE IF NOT EXISTS diagnostic_handoff_work_packages (
    id uuid PRIMARY KEY,
    handoff_id uuid NOT NULL REFERENCES diagnostic_handoffs(id) ON DELETE RESTRICT,
    work_package_id uuid NOT NULL REFERENCES work_packages(id) ON DELETE RESTRICT,
    source_recommendation_id text NOT NULL,
    evidence_references jsonb NOT NULL DEFAULT '[]'::jsonb
);
