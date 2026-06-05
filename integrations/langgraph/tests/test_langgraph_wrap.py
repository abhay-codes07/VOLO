"""Tests for `volo_langgraph.wrap` — duck-typed LangGraph shim."""

from __future__ import annotations

from typing import Any

from volo_langgraph import wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _StubGraph:
    """Mimics a LangGraph compiled graph."""

    def __init__(self) -> None:
        self.model: Any = None
        self.tools: Any = None

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        # The "graph" calls the proxied model and a proxied tool exactly once.
        self.model.complete({"prompt": state["q"]})
        out = self.tools.call("search", {"q": state["q"]})
        return {"hits": out["hits"]}


class _Model(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": request["prompt"][::-1], "stop_reason": "end_turn"}


class _Tools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {"hits": [{"title": tool, "url": "https://x/" + request["q"]}]}


def test_wrap_installs_proxies_and_records_steps() -> None:
    graph = _StubGraph()
    wrap(graph, model=_Model(), tools=_Tools(), provider_name="lg", model_name="echo-1")

    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        out = graph.invoke({"q": "volo"})
    assert out == {"hits": [{"title": "search", "url": "https://x/volo"}]}
    types = [s.type for s in rec.recording.steps]
    assert types == ["model_call", "tool_call"]
    assert rec.recording.steps[0].payload.provider == "lg"  # type: ignore[union-attr]
    assert rec.recording.steps[1].payload.tool == "search"  # type: ignore[union-attr]


def test_wrap_returns_graph_for_chaining() -> None:
    graph = _StubGraph()
    out = wrap(graph, model=_Model(), tools=_Tools())
    assert out is graph
