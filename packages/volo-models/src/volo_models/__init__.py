"""volo-models — cost-routing brain (bible §4 subsystem 7, §11).

Provider abstraction with three backends:

* ``OllamaProvider`` — default. Local small models. $0 marginal.
* ``OpenAICompatProvider`` — any OpenAI-compatible API (Groq / Gemini / OpenRouter / xAI).
  Defaults to Groq's **free** tier. Opt-in via ``VOLO_OPENAI_COMPAT_OPT_IN=true``; $0 cost.
* ``FrontierProvider`` — Anthropic / OpenAI **paid** APIs. Opt-in only, gated by
  ``VOLO_FRONTIER_OPT_IN=true`` and a per-project ``Budget`` cap.

Plus ``CachedProvider`` wrapping anything to make repeat calls free.

The Ollama HTTP client is deliberately a thin sync wrapper — the SDK's proxies handle the
heavy lifting (capture + replay). Live HTTP calls only happen at record time.
"""

from volo_models.budget import Budget, BudgetExceeded
from volo_models.cached import CachedProvider
from volo_models.frontier import FrontierProvider, FrontierUnavailable
from volo_models.ollama import OllamaProvider, OllamaUnavailable
from volo_models.openai_compat import (
    PRESETS,
    OpenAICompatProvider,
    OpenAICompatUnavailable,
)

__all__ = [
    "PRESETS",
    "Budget",
    "BudgetExceeded",
    "CachedProvider",
    "FrontierProvider",
    "FrontierUnavailable",
    "OllamaProvider",
    "OllamaUnavailable",
    "OpenAICompatProvider",
    "OpenAICompatUnavailable",
]
