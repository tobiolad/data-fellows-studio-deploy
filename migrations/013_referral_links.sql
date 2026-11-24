-- Trackable referral links for onboarded partners (e.g. accelerators). A
-- partner gets a shareable code and a separate, secret view_token so they
-- can see their own link's performance without a Studio account.
CREATE TABLE IF NOT EXISTS referral_links (
    id uuid PRIMARY KEY,
    code text NOT NULL UNIQUE CHECK (length(code) >= 6),
    view_token text NOT NULL UNIQUE CHECK (length(view_token) >= 16),
    partner_name text NOT NULL CHECK (length(trim(partner_name)) >= 2),
    created_by text NOT NULL CHECK (length(trim(created_by)) >= 2),
    status text NOT NULL CHECK (status IN ('active', 'disabled')) DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- One row per visit or signup attributed to a link. referred_organization_id
-- is set only for a 'signup' event, once an organization is created with
-- that link's code.
CREATE TABLE IF NOT EXISTS referral_events (
    id uuid PRIMARY KEY,
    link_id uuid NOT NULL REFERENCES referral_links(id) ON DELETE RESTRICT,
    event_type text NOT NULL CHECK (event_type IN ('visit', 'signup')),
    referred_organization_id uuid REFERENCES organizations(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS referral_events_link_idx ON referral_events(link_id, created_at);
