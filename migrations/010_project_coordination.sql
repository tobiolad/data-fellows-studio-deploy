CREATE TABLE project_requests (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects ON DELETE RESTRICT,
    subject text NOT NULL,
    requested_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    decision text CHECK (decision IN ('approved','declined')),
    rationale text,
    decided_by text,
    decided_at timestamptz,
    CHECK ((decision IS NULL AND rationale IS NULL AND decided_by IS NULL AND decided_at IS NULL)
        OR (decision IS NOT NULL AND rationale IS NOT NULL AND decided_by IS NOT NULL AND decided_at IS NOT NULL))
);
CREATE INDEX project_requests_timeline ON project_requests(project_id, created_at);
CREATE TABLE project_handovers (
    project_id uuid PRIMARY KEY REFERENCES projects ON DELETE RESTRICT,
    recorded_by text NOT NULL,
    versions jsonb NOT NULL CHECK (jsonb_array_length(versions) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);
