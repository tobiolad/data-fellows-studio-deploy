-- Studio-owned accounts for people who sign in with Google. Google verifies
-- the person's identity but has no notion of Studio's workspace roles, so a
-- new account starts with global_role = NULL (pending) until an admin
-- assigns one; require_global() in app.py denies every route to an identity
-- with no roles, so a brand-new Google sign-in cannot grant itself access.
CREATE TABLE IF NOT EXISTS accounts (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE CHECK (email = lower(email)),
    name text NOT NULL DEFAULT '',
    avatar_url text,
    global_role text CHECK (global_role IN ('admin', 'reviewer', 'professional', 'client')),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);
