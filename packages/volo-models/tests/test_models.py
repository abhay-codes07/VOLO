"""Tests for the cost-routing brain (bible §11)."""

from __future__ import annotations

from typing import Any

import pytest

from volo_core.interfaces import ModelProvider
from volo_models import (
    Budget,
    BudgetExceeded,
    CachedProvider,
    FrontierProvider,
    FrontierUnavailable,
    OllamaProvider,
)


class _CountingProvider(ModelProvider):
    def __init__(self) -> None:
        self.n_calls = 0

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        self.n_calls += 1
        return {"text": "ok", "n": self.n_calls}


def test_cached_provider_serves_repeat_calls_from_cache() -> None:
    inner = _CountingProvider()
    cached = CachedProvider(inner, provider="x", model="y")
    a = cached.complete({"prompt": "hi"})
    b = cached.complete({"prompt": "hi"})
    assert a == b
    assert inner.n_calls == 1
    assert cached.stats() == {"entries": 1}


def test_cached_provider_misses_for_different_requests() -> None:
    inner = _CountingProvider()
    cached = CachedProvider(inner, provider="x", model="y")
    cached.complete({"prompt": "hi"})
    cached.complete({"prompt": "bye"})
    assert inner.n_calls == 2


def test_budget_blocks_overrun() -> None:
    b = Budget(max_usd=0.01)
    b.charge(0.009)
    with pytest.raises(BudgetExceeded):
        b.check(0.005)


def test_frontier_refuses_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOLO_FRONTIER_OPT_IN", raising=False)
    fp = FrontierProvider(budget=Budget(max_usd=10.0))
    with pytest.raises(FrontierUnavailable, match="opt-in"):
        fp.complete({"prompt": "hi"})


def test_frontier_refuses_without_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_FRONTIER_OPT_IN", "true")
    fp = FrontierProvider(budget=None)
    with pytest.raises(FrontierUnavailable, match="Budget"):
        fp.complete({"prompt": "hi"})


def test_frontier_enforces_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_FRONTIER_OPT_IN", "true")
    fp = FrontierProvider(
        model="claude-opus-4-7",
        budget=Budget(max_usd=0.0001),  # tiny cap
        _inner=_CountingProvider(),
    )
    with pytest.raises(BudgetExceeded):
        fp.complete({"prompt": "hi", "max_input_tokens": 1000, "max_output_tokens": 500})


def test_frontier_passes_through_when_within_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_FRONTIER_OPT_IN", "true")
    inner = _CountingProvider()
    budget = Budget(max_usd=10.0)
    fp = FrontierProvider(model="claude-haiku-4-5", budget=budget, _inner=inner)
    out = fp.complete({"prompt": "hi", "max_input_tokens": 100, "max_output_tokens": 100})
    assert out["text"] == "ok"
    assert out["_cost_usd"] > 0
    assert budget.spent_usd > 0
    assert inner.n_calls == 1


def test_ollama_unavailable_when_daemon_missing() -> None:
    from volo_models import OllamaUnavailable

    ollama = OllamaProvider(host="http://127.0.0.1:1")  # almost certainly closed
    with pytest.raises(OllamaUnavailable):
        ollama.complete({"prompt": "hi"})
