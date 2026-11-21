-- Project-scoped collaboration records. These are metadata-only references:
-- binary files remain in private object storage and are never exposed as URLs.
CREATE TABLE IF NOT EXISTS project_messages (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    sender_id text NOT NULL CHECK (length(trim(sender_id)) >= 2),
    recipient_group text NOT NULL CHECK (recipient_group IN ('client', 'professional', 'internal')),
    body text NOT NULL CHECK (length(trim(body)) BETWEEN 2 AND 4000),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_messages_project_idx
    ON project_messages(project_id, created_at);

CREATE TABLE IF NOT EXISTS project_documents (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(trim(name)) BETWEEN 2 AND 200),
    description text NOT NULL DEFAULT '',
    classification text NOT NULL CHECK (classification IN ('project', 'deliverable', 'support')),
    storage_reference text NOT NULL CHECK (length(trim(storage_reference)) BETWEEN 2 AND 512),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_documents_project_idx
    ON project_documents(project_id, created_at);

CREATE TABLE IF NOT EXISTS notifications (
    id uuid PRIMARY KEY,
    project_id uuid REFERENCES projects(id) ON DELETE RESTRICT,
    recipient_group text NOT NULL CHECK (recipient_group IN ('client', 'professional', 'internal')),
    kind text NOT NULL CHECK (length(trim(kind)) >= 2),
    title text NOT NULL CHECK (length(trim(title)) >= 2),
    body text NOT NULL CHECK (length(trim(body)) >= 2),
    read_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notifications_project_idx
    ON notifications(project_id, created_at);
