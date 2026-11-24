-- AI agent registry: persisted, policy-governed records describing every
-- agent allowed to request an AI run. Runs must resolve to an active,
-- registered agent instead of an inline literal.
CREATE TABLE IF NOT EXISTS ai_agents (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (length(trim(name)) >= 2),
    purpose text NOT NULL CHECK (length(trim(purpose)) >= 2),
    capability_category text NOT NULL CHECK (capability_category IN ('planning', 'research', 'code_generation', 'qa', 'vetting', 'analytics')),
    provider text NOT NULL CHECK (length(trim(provider)) >= 2),
    model text NOT NULL CHECK (length(trim(model)) >= 1),
    model_version text NOT NULL CHECK (length(trim(model_version)) >= 1),
    allowed_tools jsonb NOT NULL,
    data_access_scope text NOT NULL CHECK (data_access_scope IN ('none', 'work_package', 'organization')),
    autonomy_level text NOT NULL CHECK (autonomy_level IN ('supervised', 'bounded_autonomous')),
    requires_human_approval boolean NOT NULL DEFAULT true,
    budget_cap_cents integer NOT NULL CHECK (budget_cap_cents > 0),
    owner_actor_id text NOT NULL CHECK (length(trim(owner_actor_id)) >= 2),
    status text NOT NULL CHECK (status IN ('active', 'disabled')) DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Bind each run to the registered agent that produced it, and record the
-- provider/model provenance the model gateway returned, instead of the
-- inline literal the route handler used to hardcode.
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS agent_id uuid REFERENCES ai_agents(id);
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS provider text;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS model text;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS model_version text;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS input_tokens integer NOT NULL DEFAULT 0;
ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS output_tokens integer NOT NULL DEFAULT 0;

-- Seed the existing deterministic executor as the first registry row so
-- every prior run and test keeps resolving to the same agent by default.
INSERT INTO ai_agents (
    id, name, purpose, capability_category, provider, model, model_version,
    allowed_tools, data_access_scope, autonomy_level, requires_human_approval,
    budget_cap_cents, owner_actor_id, status
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'synthetic-planner-v1',
    'Deterministic, bounded work-breakdown planning used for CI and reviewer-gated delivery.',
    'planning',
    'synthetic',
    'planner',
    'planning-only-v1',
    '["planning"]'::jsonb,
    'work_package',
    'supervised',
    true,
    1000,
    'platform',
    'active'
) ON CONFLICT (id) DO NOTHING;
