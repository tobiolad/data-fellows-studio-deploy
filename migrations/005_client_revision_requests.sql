-- Client decisions remain separate from internal reviewer decisions.
CREATE TABLE IF NOT EXISTS client_revision_requests (
    id uuid PRIMARY KEY,
    deliverable_id uuid NOT NULL REFERENCES deliverables(id) ON DELETE RESTRICT,
    client_id text NOT NULL,
    comment text NOT NULL CHECK (length(trim(comment)) >= 2),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS client_revision_requests_deliverable_idx
    ON client_revision_requests(deliverable_id, created_at);
