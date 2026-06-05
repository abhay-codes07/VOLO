"""Tests for `volo_crewai.wrap` — Crew-style agents + kickoff decoration."""

from __future__ import annotations

from typing import Any

from volo_crewai import wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _Agent:
    def __init__(self) -> None:
        self.llm: Any = None
        self.tools: Any = None


class _Crew:
    def __init__(self) -> None:
        self.agents = [_Agent(), _Agent()]
        self.kicked = False

    def kickoff(self) -> str:
        self.kicked = True
        # Each agent calls its llm once.
        for a in self.agents:
            a.llm.complete({"prompt": "step"})
        return "done"


class _Echo(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": "ok", "stop_reason": "end_turn"}


class _NoopTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {}


def test_wrap_proxies_each_agent_llm_and_records_kickoff_decision() -> None:
    crew = _Crew()
    wrap(crew, model=_Echo(), tools=_NoopTools())
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        out = crew.kickoff()
    assert out == "done"
    assert crew.kicked is True
    types = [s.type for s in rec.recording.steps]
    # 1 decision (kickoff) + 2 model_call (one per agent)
    assert types == ["decision", "model_call", "model_call"]
    assert rec.recording.steps[0].payload.label == "crew_kickoff"  # type: ignore[union-attr]
