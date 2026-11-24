# Controlled AI execution

## Agent registry

Every AI run resolves to a row in `ai_agents` (migration `011_agent_registry.sql`) instead of an inline literal. A registry row records name, purpose, capability category, provider, model, model version, the exact tools it may use, its data access scope, autonomy level, whether human approval is required, a budget cap in cents, the responsible human owner, and a lifecycle status (`active`/`disabled`). `POST /api/ai-agents` (admin only) registers a new agent; `GET /api/ai-agents` (admin or reviewer) lists the registry. The deterministic planner is seeded as a fixed-UUID row (`synthetic-planner-v1`, provider `synthetic`) so every run that omits `agent_id` resolves to the same registry entry the previous hardcoded literal represented.

A run request (`POST /api/ai-runs`) must pass an `agent_id` referencing an active registry row (or omit it to use the seeded synthetic planner). The requested tools must be a subset of the agent's `allowed_tools`, and the requested `budget_cents` must not exceed the agent's `budget_cap_cents` — both enforced server-side before any execution is attempted.

## Model gateway

`backend/model_gateway.py` is the single policy boundary between a run request and a provider. `resolve_adapter(provider)` returns the adapter authorized to execute a given provider's runs. The only adapter shipped today is `SyntheticPlannerAdapter` (provider `synthetic`) — a deterministic executor that can produce only a structured work breakdown, never a real model call. Any other provider is refused unless the deployment sets `STUDIO_AI_REAL_PROVIDER_APPROVED=1`, which records that an operator reviewed and budgeted that provider; the gateway still has no adapter registered for a real provider, so setting the flag alone cannot cause a real-model call — wiring one in is a separate, explicitly reviewed change. CI and local tests always exercise the synthetic adapter, so they remain fully repeatable without network access, API keys or spend.

An adapter run returns provider, model, model version, token counts and cost (all zero for the synthetic adapter) alongside its output. These are persisted on the `ai_runs` row (`agent_id`, `provider`, `model`, `model_version`, `input_tokens`, `output_tokens`) so execution provenance is auditable per run, not just per deployment.

## Execution and review policy (unchanged)

Each run records the requesting identity, work package, agent version, allowed tool, budget, spent amount, status and output artifact. The requester cannot approve its own artifact, regardless of the agent's `requires_human_approval` flag — that flag is a recorded governance signal for future autonomy tiers, not a bypass of the existing independent-review gate. The artifact must be approved before it can support a delivery workflow.

Future model adapters must preserve the same policy boundary and add provider/model version, token/cost accounting, timeout, retry and content-safety metadata. No agent may deploy, make payments, contact a client, expand scope or grant permissions from this interface.
