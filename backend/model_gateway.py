"""Model gateway: one policy boundary behind pluggable provider adapters.

Every AI run is routed through `resolve_adapter`, never by importing a
provider SDK directly from a route handler. The only adapter shipped here is
the deterministic synthetic executor, so CI and local tests stay fully
repeatable without network access, API keys or spend. Routing a run to any
other provider requires an operator to set `STUDIO_AI_REAL_PROVIDER_APPROVED=1`
on the running service, which only records that a human has reviewed and
budgeted that provider for use; no real adapter is registered by this
module, so setting the flag alone still cannot execute a real-model call.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

REAL_PROVIDER_APPROVAL_ENV = "STUDIO_AI_REAL_PROVIDER_APPROVED"


class ModelGatewayError(Exception):
    """Raised when a run cannot be routed to, or executed by, an adapter."""


@dataclass(frozen=True)
class AdapterResult:
    output: dict[str, Any]
    provider: str
    model: str
    model_version: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: int = 0
    tool_calls: list[str] = field(default_factory=list)


class ModelAdapter:
    provider: str = "unknown"

    def run(self, specification: str, allowed_tools: list[str]) -> AdapterResult:
        raise NotImplementedError


class SyntheticPlannerAdapter(ModelAdapter):
    """Deterministic test/CI executor. Produces only a bounded work breakdown."""

    provider = "synthetic"
    model = "planner"
    model_version = "planning-only-v1"

    def run(self, specification: str, allowed_tools: list[str]) -> AdapterResult:
        if allowed_tools != ["planning"]:
            raise ModelGatewayError("Only the bounded planning tool is enabled")
        output = {
            "type": "work_breakdown",
            "synthetic": True,
            "steps": [
                {"order": 1, "title": "Clarify approved requirements", "requires_approval": True},
                {"order": 2, "title": "Prepare implementation checklist", "requires_approval": True},
                {"order": 3, "title": "Review acceptance criteria", "requires_approval": True},
            ],
            "source_specification": specification,
        }
        return AdapterResult(
            output=output,
            provider=self.provider,
            model=self.model,
            model_version=self.model_version,
            tool_calls=["planning"],
        )


def resolve_adapter(provider: str) -> ModelAdapter:
    """Return the adapter authorized to execute runs for `provider`.

    Raises ModelGatewayError for any provider this deployment is not
    configured and approved to call, including every real provider today.
    """
    if provider == SyntheticPlannerAdapter.provider:
        return SyntheticPlannerAdapter()
    if os.getenv(REAL_PROVIDER_APPROVAL_ENV, "").strip() != "1":
        raise ModelGatewayError(
            f"Provider '{provider}' is not approved for execution. An operator must "
            f"configure a reviewed, budgeted adapter and set {REAL_PROVIDER_APPROVAL_ENV}=1 "
            "before any run can be routed to it."
        )
    raise ModelGatewayError(f"No adapter is registered for approved provider '{provider}'")
