"""Tests for the optional judge layer (ADR-0006 + ADR-0009)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from volo_core import ModelCallPayload, Recording, ToolCallPayload
from volo_core.interfaces import ModelProvider
from volo_reliability import (
    FrontierJudge,
    HeuristicJudge,
    OllamaJudge,
    OpenAICompatJudge,
    default_judge,
    faithfulness,
)


def _grounded_recording() -> Recording:
    r = Recording()
    r.add_step(ToolCallPayload(tool="add", request={"a": 2, "b": 3}, response={"result": 5}))
    r.final_output = {"answer": 5}
    return r


def _ungrounded_recording() -> Recording:
    r = Recording()
    r.add_step(ToolCallPayload(tool="add", request={"a": 2, "b": 3}, response={"result": 5}))
    r.final_output = {"answer": "totally fabricated"}
    return r


class _ScriptedProvider(ModelProvider):
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self._responses:
            return {"text": "{}"}
        return {"text": self._responses.pop(0)}


# ── heuristic ────────────────────────────────────────────────────────────────


def test_heuristic_grounded() -> None:
    assert HeuristicJudge().score(_grounded_recording()) == 1.0


def test_heuristic_ungrounded() -> None:
    assert HeuristicJudge().score(_ungrounded_recording()) == 0.0


def test_faithfulness_default_is_heuristic() -> None:
    assert faithfulness(_grounded_recording()) == 1.0
    assert faithfulness(_ungrounded_recording()) == 0.0


def test_faithfulness_accepts_explicit_judge() -> None:
    class _Always(_ScriptedProvider):
        pass

    judge = OllamaJudge(provider=_Always([json.dumps({"score": 0.7})]))
    assert faithfulness(_grounded_recording(), judge=judge) == 0.7


# ── OllamaJudge ──────────────────────────────────────────────────────────────


def test_ollama_judge_falls_back_to_heuristic_on_malformed_output() -> None:
    judge = OllamaJudge(provider=_ScriptedProvider(["totally not json"]))
    # Heuristic returns 1.0 on grounded recording.
    assert judge.score(_grounded_recording()) == 1.0


def test_ollama_judge_clamps_to_zero_one() -> None:
    judge = OllamaJudge(provider=_ScriptedProvider([json.dumps({"score": 7.5})]))
    assert judge.score(_grounded_recording()) == 1.0


# ── OpenAICompatJudge (free; Groq default) ───────────────────────────────────


def test_openai_compat_judge_scores_from_provider() -> None:
    judge = OpenAICompatJudge(provider=_ScriptedProvider([json.dumps({"score": 0.91})]))
    assert judge.score(_grounded_recording()) == 0.91


def test_openai_compat_judge_falls_back_on_malformed_output() -> None:
    judge = OpenAICompatJudge(provider=_ScriptedProvider(["not json at all"]))
    # Heuristic returns 1.0 on the grounded recording.
    assert judge.score(_grounded_recording()) == 1.0


def test_openai_compat_judge_falls_back_when_provider_unavailable() -> None:
    class _Boom(_ScriptedProvider):
        def complete(self, request: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("backend down")

    judge = OpenAICompatJudge(provider=_Boom([]))
    assert judge.score(_ungrounded_recording()) == 0.0  # heuristic fallback


def test_default_judge_swaps_to_openai_compat_when_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VOLO_OLLAMA_JUDGE", raising=False)
    monkeypatch.setenv("VOLO_OPENAI_COMPAT_JUDGE", "true")
    assert isinstance(default_judge(), OpenAICompatJudge)


# ── FrontierJudge gating ─────────────────────────────────────────────────────


def test_frontier_judge_refuses_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    from volo_models import Budget

    monkeypatch.delenv("VOLO_FRONTIER_OPT_IN", raising=False)
    with pytest.raises(RuntimeError, match=r"opt-in|OPT_IN"):
        FrontierJudge(inner=_ScriptedProvider([]), budget=Budget(max_usd=1.0))


def test_frontier_judge_refuses_without_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_FRONTIER_OPT_IN", "true")
    with pytest.raises(RuntimeError, match="Budget"):
        FrontierJudge(inner=_ScriptedProvider([]), budget=None)


def test_frontier_judge_passes_through_when_within_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from volo_models import Budget

    monkeypatch.setenv("VOLO_FRONTIER_OPT_IN", "true")
    inner = _ScriptedProvider([json.dumps({"score": 0.83})])
    judge = FrontierJudge(inner=inner, budget=Budget(max_usd=10.0))
    assert judge.score(_grounded_recording()) == 0.83


# ── env-driven factory ───────────────────────────────────────────────────────


def test_default_judge_is_heuristic_unless_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOLO_OLLAMA_JUDGE", raising=False)
    monkeypatch.delenv("VOLO_OPENAI_COMPAT_JUDGE", raising=False)
    assert isinstance(default_judge(), HeuristicJudge)


def test_default_judge_swaps_when_env_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_OLLAMA_JUDGE", "true")
    assert isinstance(default_judge(), OllamaJudge)


# ── aggregate_runs honours a supplied judge ──────────────────────────────────


def test_aggregate_runs_uses_supplied_judge() -> None:
    from volo_reliability import aggregate_runs

    # Grounded recording → heuristic would score 1.0; the judge forces 0.5.
    judge = OllamaJudge(provider=_ScriptedProvider([json.dumps({"score": 0.5})]))
    sub = aggregate_runs(
        [_grounded_recording()],
        scenario_op="x",
        failure_class="y",
        seed=0,
        judge=judge,
    )
    assert sub.metrics["faithfulness"] == 0.5


def test_aggregate_runs_defaults_to_heuristic() -> None:
    from volo_reliability import aggregate_runs

    sub = aggregate_runs([_grounded_recording()], scenario_op="x", failure_class="y", seed=0)
    assert sub.metrics["faithfulness"] == 1.0


# ── evidence summary doesn't crash on mixed step types ───────────────────────


def test_judge_handles_mixed_step_types() -> None:
    r = Recording()
    r.add_step(ToolCallPayload(tool="t", request={}, response={"x": 1}))
    r.add_step(
        ModelCallPayload(provider="p", model="m", request={"q": "?"}, response={"text": "y"})
    )
    r.final_output = {"x": 1}
    judge = OllamaJudge(provider=_ScriptedProvider([json.dumps({"score": 0.5})]))
    assert judge.score(r) == 0.5
