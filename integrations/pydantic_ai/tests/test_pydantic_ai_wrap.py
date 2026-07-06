"""Tests for `volo_pydantic_ai.wrap` — Agent.model swap + run_sync decoration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_pydantic_ai import import_pydantic_ai_otel, wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _Echo(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": "ok", "stop_reason": "end_turn"}


class _NoopTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {}


class _Agent:
    def __init__(self) -> None:
        self.model: Any = None

    def run_sync(self, prompt: str) -> str:
        self.model.complete({"prompt": prompt})
        return f"answer:{prompt}"


def test_wrap_records_decision_and_model_call() -> None:
    agent = wrap(_Agent(), model=_Echo(), tools=_NoopTools())
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        assert agent.run_sync("hi") == "answer:hi"
    types = [s.type for s in rec.recording.steps]
    assert types == ["decision", "model_call"]
    assert rec.recording.steps[0].payload.label == "pydantic_ai_run"  # type: ignore[union-attr]
    assert agent._volo_tool_proxy is not None


def test_import_pydantic_ai_otel_framework(tmp_path: Path) -> None:
    trace = tmp_path / "t.jsonl"
    trace.write_text(
        '{"name":"gen_ai.chat","spanId":"s1","startTimeUnixNano":1,'
        '"attributes":{"gen_ai.system":"openai","gen_ai.request.model":"gpt",'
        '"gen_ai.response":"{\\"text\\":\\"ok\\"}"}}\n',
        encoding="utf-8",
    )
    rec = import_pydantic_ai_otel(trace, agent_name="a")
    assert rec.agent_meta.framework == "pydantic_ai" and len(rec.steps) == 1
