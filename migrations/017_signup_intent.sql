-- A self-reported hint of what a newly signed-in account came to Studio
-- for, shown to the admin deciding their role ("Jordan says: applying as
-- a professional") so the admin isn't left guessing from a bare email
-- address. Purely informational: it grants no role or access, and no
-- authorization check anywhere reads it.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS signup_intent text
    CHECK (signup_intent IN ('professional', 'client', 'team'));
