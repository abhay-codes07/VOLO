"""Cost budget enforcement for frontier providers (bible §11)."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    """Raised when a frontier call would exceed the configured cap."""


@dataclass
class Budget:
    max_usd: float
    spent_usd: float = 0.0

    def check(self, projected_cost_usd: float) -> None:
        if self.spent_usd + projected_cost_usd > self.max_usd:
            raise BudgetExceeded(
                f"projected cost ${projected_cost_usd:.4f} would exceed cap "
                f"${self.max_usd:.4f} (already spent ${self.spent_usd:.4f}).",
            )

    def charge(self, cost_usd: float) -> None:
        self.spent_usd += cost_usd
