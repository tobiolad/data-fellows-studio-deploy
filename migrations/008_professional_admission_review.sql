-- Admission review metadata is deliberately separate from profile completeness.
-- Evidence references are metadata-only until private quarantine and scanning are
-- configured; no file bytes or public URLs are accepted by the API.
ALTER TABLE professional_admissions
    DROP CONSTRAINT IF EXISTS professional_admissions_status_check;

ALTER TABLE professional_admissions
    ADD CONSTRAINT professional_admissions_status_check
    CHECK (status IN ('draft', 'submitted', 'under_review', 'assessment', 'approved', 'declined', 'pending', 'rejected', 'revoked'));

ALTER TABLE professional_admissions
    ADD COLUMN IF NOT EXISTS submitted_at timestamptz,
    ADD COLUMN IF NOT EXISTS reviewed_at timestamptz,
    ADD COLUMN IF NOT EXISTS decision_reason text NOT NULL DEFAULT '' CHECK (length(decision_reason) <= 4000),
    ADD COLUMN IF NOT EXISTS missing_information jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS assessment_requests jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS evidence_references jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS next_action text NOT NULL DEFAULT '' CHECK (length(next_action) <= 1000);

ALTER TABLE professional_admissions
    ADD CONSTRAINT professional_admissions_missing_information_array
    CHECK (jsonb_typeof(missing_information) = 'array');
ALTER TABLE professional_admissions
    ADD CONSTRAINT professional_admissions_assessment_requests_array
    CHECK (jsonb_typeof(assessment_requests) = 'array');
ALTER TABLE professional_admissions
    ADD CONSTRAINT professional_admissions_evidence_references_array
    CHECK (jsonb_typeof(evidence_references) = 'array');

ALTER TABLE professional_profiles
    ADD COLUMN IF NOT EXISTS evidence_references jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE professional_profiles
    ADD CONSTRAINT professional_profiles_evidence_references_array
    CHECK (jsonb_typeof(evidence_references) = 'array');

CREATE INDEX IF NOT EXISTS professional_admissions_review_queue_idx
    ON professional_admissions(status, created_at DESC);
