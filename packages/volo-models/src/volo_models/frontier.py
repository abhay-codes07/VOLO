"""``FrontierProvider`` — gated abstraction over Anthropic / OpenAI (bible §11).

Refuses to make a call unless:
1. ``VOLO_FRONTIER_OPT_IN`` env var is the string ``"true"``;
2. a ``Budget`` is supplied AND the projected cost fits.

This is the only place in the codebase that can spend real money, by design.
"""

from __future__ import annotations

import os
from typing import Any

from volo_core.interfaces import ModelProvider
from volo_models.budget import Budget, BudgetExceeded
from volo_models.pricing import estimate_cost_usd


class FrontierUnavailable(RuntimeError):
    """Raised when the user has not opted into frontier calls or has no provider configured."""


def _projected_cost_usd(model: str, request: dict[str, Any]) -> float:
    in_tokens = int(request.get("max_input_tokens", 1000))
    out_tokens = int(request.get("max_output_tokens", 500))
    return estimate_cost_usd(model, in_tokens, out_tokens)


class FrontierProvider(ModelProvider):
    def __init__(
        self,
        *,
        provider: str = "anthropic",
        model: str = "claude-haiku-4-5",
        budget: Budget | None = None,
        _inner: ModelProvider | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.budget = budget
        # _inner is the testing seam: real implementations call out to the network here.
        self._inner = _inner

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        if os.environ.get("VOLO_FRONTIER_OPT_IN", "false").lower() != "true":
            raise FrontierUnavailable(
                "frontier API calls are opt-in. Set VOLO_FRONTIER_OPT_IN=true to enable.",
            )
        cost = _projected_cost_usd(self.model, request)
        if self.budget is None:
            raise FrontierUnavailable(
                "no Budget supplied — refusing to make a paid call without an explicit cap.",
            )
        try:
            self.budget.check(cost)
        except BudgetExceeded:
            raise
        if self._inner is None:
            raise FrontierUnavailable(
                f"no concrete client wired for provider={self.provider!r}; "
                f"plug one in via the _inner argument or a framework adapter.",
            )
        response = self._inner.complete(request)
        self.budget.charge(cost)
        response.setdefault("_cost_usd", cost)
        response.setdefault("_provider", self.provider)
        response.setdefault("_model", self.model)
        return response
