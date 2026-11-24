ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS cancel_requested boolean NOT NULL DEFAULT false;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS error_code text;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS started_at timestamptz;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS finished_at timestamptz;

UPDATE ai_runs
SET started_at = COALESCE(started_at, created_at),
    finished_at = COALESCE(finished_at, created_at)
WHERE status IN ('succeeded', 'failed', 'cancelled');

ALTER TABLE ai_runs DROP CONSTRAINT IF EXISTS ai_runs_terminal_timestamp_check;
ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_terminal_timestamp_check
    CHECK (status NOT IN ('succeeded', 'failed', 'cancelled') OR finished_at IS NOT NULL);
