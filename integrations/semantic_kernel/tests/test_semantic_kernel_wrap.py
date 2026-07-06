"""Tests for `volo_semantic_kernel.wrap` — services swap + invoke decoration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_semantic_kernel import import_semantic_kernel_otel, wrap

from volo_core import current_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import Recorder, RecorderConfig


class _Echo(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": "ok", "stop_reason": "end_turn"}


class _NoopTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        return {}


class _Kernel:
    """Semantic Kernel shape: services dict + plugins + invoke()."""

    def __init__(self) -> None:
        self.services: dict[str, Any] = {"chat": object()}
        self.plugins: dict[str, Any] = {}

    def invoke(self, prompt: str) -> str:
        self.services["chat"].complete({"prompt": prompt})
        return f"kernel:{prompt}"


def test_wrap_swaps_services_and_records() -> None:
    kernel = wrap(_Kernel(), model=_Echo(), tools=_NoopTools())
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        assert kernel.invoke("go") == "kernel:go"
    types = [s.type for s in rec.recording.steps]
    assert types == ["decision", "model_call"]
    assert rec.recording.steps[0].payload.label == "kernel_invoke"  # type: ignore[union-attr]
    assert kernel._volo_tool_proxy is not None


def test_wrap_swaps_every_service() -> None:
    kernel = _Kernel()
    kernel.services = {"a": object(), "b": object()}
    wrap(kernel, model=_Echo())
    assert all(hasattr(svc, "complete") for svc in kernel.services.values())


def test_import_semantic_kernel_otel_framework(tmp_path: Path) -> None:
    trace = tmp_path / "t.jsonl"
    trace.write_text(
        '{"name":"tool.search","spanId":"s1","startTimeUnixNano":1,'
        '"attributes":{"tool.name":"search","tool.output":"{\\"hits\\":1}"}}\n',
        encoding="utf-8",
    )
    rec = import_semantic_kernel_otel(trace, agent_name="a")
    assert rec.agent_meta.framework == "semantic_kernel" and len(rec.steps) == 1
