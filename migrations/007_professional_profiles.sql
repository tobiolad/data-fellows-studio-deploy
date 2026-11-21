-- Structured professional profile drafts remain separate from admission decisions.
-- A complete profile never grants delivery access; admission and assignment checks
-- continue to be enforced by the existing API.
CREATE TABLE IF NOT EXISTS professional_profiles (
    professional_id text PRIMARY KEY REFERENCES professional_admissions(professional_id) ON DELETE RESTRICT,
    display_name text NOT NULL CHECK (length(trim(display_name)) BETWEEN 2 AND 160),
    headline text NOT NULL DEFAULT '' CHECK (length(headline) <= 240),
    bio text NOT NULL DEFAULT '' CHECK (length(bio) <= 4000),
    skills jsonb NOT NULL DEFAULT '[]'::jsonb,
    specializations jsonb NOT NULL DEFAULT '[]'::jsonb,
    education jsonb NOT NULL DEFAULT '[]'::jsonb,
    experience jsonb NOT NULL DEFAULT '[]'::jsonb,
    portfolio jsonb NOT NULL DEFAULT '[]'::jsonb,
    availability text NOT NULL DEFAULT '' CHECK (length(availability) <= 120),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(skills) = 'array'),
    CHECK (jsonb_typeof(specializations) = 'array'),
    CHECK (jsonb_typeof(education) = 'array'),
    CHECK (jsonb_typeof(experience) = 'array'),
    CHECK (jsonb_typeof(portfolio) = 'array')
);

CREATE INDEX IF NOT EXISTS professional_profiles_updated_idx
    ON professional_profiles(updated_at DESC);
