"""Tests for `volo_autogen.wrap` — v0.4 (`model_client`) + legacy (`llm`) shapes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_autogen import import_autogen_otel, wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _Echo(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": "ok", "stop_reason": "end_turn"}


class _NoopTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {}


class _V04Agent:
    """AutoGen v0.4 shape: model_client + run()."""

    def __init__(self) -> None:
        self.model_client: Any = None
        self.tools: Any = None

    def run(self) -> str:
        self.model_client.complete({"prompt": "step"})
        return "done"


class _LegacyAgent:
    """AutoGen 0.2 shape: llm + generate_reply()."""

    def __init__(self) -> None:
        self.llm: Any = None

    def generate_reply(self) -> str:
        self.llm.complete({"prompt": "step"})
        return "reply"


def test_wrap_v04_records_decision_and_model_call() -> None:
    agent = wrap(_V04Agent(), model=_Echo(), tools=_NoopTools())
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        assert agent.run() == "done"
    types = [s.type for s in rec.recording.steps]
    assert types == ["decision", "model_call"]
    assert rec.recording.steps[0].payload.label == "autogen_run"  # type: ignore[union-attr]


def test_wrap_legacy_llm_shape() -> None:
    agent = wrap(_LegacyAgent(), model=_Echo())
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        assert agent.generate_reply() == "reply"
    types = [s.type for s in rec.recording.steps]
    assert types == ["decision", "model_call"]


def test_import_autogen_otel_sets_framework(tmp_path: Path) -> None:
    trace = tmp_path / "t.jsonl"
    trace.write_text(
        '{"name":"tool.search","spanId":"s1","startTimeUnixNano":1,'
        '"attributes":{"tool.name":"search","tool.output":"{\\"hits\\":1}"}}\n',
        encoding="utf-8",
    )
    rec = import_autogen_otel(trace, agent_name="a")
    assert rec.agent_meta.framework == "autogen" and len(rec.steps) == 1
