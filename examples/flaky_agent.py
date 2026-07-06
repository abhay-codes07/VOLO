"""A deliberately unreliable agent — nondeterministic output across runs.

Uses a process-global counter so repeated runs disagree, tanking decision_determinism and
consistency-under-repetition. It exists to demonstrate the reliability leaderboard ranking an
unreliable agent well below the stable ones — the discrimination the score is supposed to have.
"""

from __future__ import annotations

import itertools
from typing import Any

from volo_core.interfaces import ModelProvider
from volo_sdk import ModelProviderProxy

_counter = itertools.count()


class _Model(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": str(request.get("prompt", "")), "stop_reason": "end_turn"}


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Take one model step, then return a different answer every time it's called."""
    model = ModelProviderProxy(_Model(), provider_name="echo", model_name="echo-1")
    model.complete({"prompt": "step"})
    return {"answer": f"draft-{next(_counter)}"}
