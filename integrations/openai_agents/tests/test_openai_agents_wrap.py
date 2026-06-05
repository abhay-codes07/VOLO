"""Tests for `volo_openai_agents.wrap`."""

from __future__ import annotations

from typing import Any

from volo_openai_agents import wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _StubAgent:
    def __init__(self) -> None:
        self.model: Any = None
        self.tools: list[Any] = []
        self._volo_tool_proxy: Any = None

    def run(self, q: str) -> str:
        text = self.model.complete({"prompt": q})["text"]
        return text


class _Echo(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": request["prompt"].upper(), "stop_reason": "end_turn"}


class _NoopTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {}


def test_wrap_records_model_call_through_proxy() -> None:
    agent = _StubAgent()
    wrap(agent, model=_Echo(), tools=_NoopTools(), provider_name="openai", model_name="gpt-4o")
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        out = agent.run("hi")
    assert out == "HI"
    assert len(rec.recording.steps) == 1
    assert rec.recording.steps[0].payload.provider == "openai"  # type: ignore[union-attr]
