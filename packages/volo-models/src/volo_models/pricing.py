"""Model pricing — USD per 1K tokens (bible §11).

Placeholder-but-plausible figures; refresh from provider price sheets as they move. Shared by
the ``FrontierProvider`` budget projection and the migration lab's cost delta.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pricing:
    """USD per 1K tokens (input, output)."""

    input_per_1k: float
    output_per_1k: float


# Keyed by bare model id. Unknown models fall back to ``DEFAULT_PRICING``.
PRICING: dict[str, Pricing] = {
    "claude-haiku-4-5": Pricing(0.0008, 0.004),
    "claude-sonnet-4-6": Pricing(0.003, 0.015),
    "claude-opus-4-7": Pricing(0.015, 0.075),
    "gpt-4.1-mini": Pricing(0.0004, 0.0016),
    "gpt-4.1": Pricing(0.002, 0.008),
    "llama3.2:3b": Pricing(0.0, 0.0),  # local via Ollama — free
    "llama-3.3-70b-versatile": Pricing(0.0, 0.0),  # Groq free tier
}

DEFAULT_PRICING = Pricing(0.005, 0.015)


def model_pricing(model: str) -> Pricing:
    """Pricing for ``model``, or the conservative default if unknown."""
    return PRICING.get(model, DEFAULT_PRICING)


def estimate_cost_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    """Projected USD cost for a call of the given token shape."""
    p = model_pricing(model)
    return in_tokens / 1000 * p.input_per_1k + out_tokens / 1000 * p.output_per_1k
