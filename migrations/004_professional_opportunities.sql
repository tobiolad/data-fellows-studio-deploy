-- Sanitized opportunities are published to approved professionals only.
CREATE TABLE IF NOT EXISTS opportunities (
    id uuid PRIMARY KEY,
    title text NOT NULL CHECK (length(trim(title)) >= 2),
    summary text NOT NULL CHECK (length(trim(summary)) >= 2),
    specialization text NOT NULL CHECK (length(trim(specialization)) >= 2),
    skills jsonb NOT NULL DEFAULT '[]'::jsonb,
    compensation text,
    deadline timestamptz,
    status text NOT NULL CHECK (status IN ('published', 'closed')),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opportunity_interests (
    id uuid PRIMARY KEY,
    opportunity_id uuid NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
    professional_id text NOT NULL,
    approach text NOT NULL CHECK (length(trim(approach)) >= 2),
    status text NOT NULL CHECK (status IN ('interested', 'selected', 'withdrawn')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (opportunity_id, professional_id)
);

CREATE INDEX IF NOT EXISTS opportunities_status_idx ON opportunities(status, created_at);
CREATE INDEX IF NOT EXISTS opportunity_interests_professional_idx ON opportunity_interests(professional_id, status);
