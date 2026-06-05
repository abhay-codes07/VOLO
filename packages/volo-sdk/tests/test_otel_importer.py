"""Tests for the real OTel trace importer (M7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from volo_sdk import import_otel_trace

# ── helpers ──────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, spans: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(s) for s in spans), encoding="utf-8")


def _write_otlp(
    path: Path, spans: list[dict[str, Any]], resource_attrs: dict[str, str] | None = None
) -> None:
    resource_kv = [
        {"key": k, "value": {"stringValue": v}} for k, v in (resource_attrs or {}).items()
    ]
    doc = {
        "resourceSpans": [
            {
                "resource": {"attributes": resource_kv},
                "scopeSpans": [{"spans": spans}],
            },
        ],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")


# ── jsonl format ─────────────────────────────────────────────────────────────


def test_jsonl_llm_span_becomes_model_call(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "llm.completion",
                "spanId": "s1",
                "startTimeUnixNano": 1_000_000_000,
                "endTimeUnixNano": 1_002_000_000,
                "attributes": {
                    "gen_ai.system": "anthropic",
                    "gen_ai.request.model": "claude-haiku",
                    "gen_ai.request": {"prompt": "hi"},
                    "gen_ai.response": {"text": "hello"},
                    "gen_ai.usage.total_tokens": 17,
                },
            },
        ],
    )
    rec = import_otel_trace(path, agent_name="demo", framework="otel")
    assert len(rec.steps) == 1
    step = rec.steps[0]
    assert step.type == "model_call"
    payload = step.payload
    assert payload.provider == "anthropic"  # type: ignore[union-attr]
    assert payload.model == "claude-haiku"  # type: ignore[union-attr]
    assert payload.request == {"prompt": "hi"}  # type: ignore[union-attr]
    assert payload.response == {"text": "hello"}  # type: ignore[union-attr]
    assert step.tokens == 17
    assert step.latency_ms == 2.0


def test_jsonl_tool_span_becomes_tool_call(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "tool.search",
                "spanId": "s1",
                "attributes": {
                    "tool.name": "search",
                    "tool.input": {"q": "volo"},
                    "tool.output": {"hits": [{"title": "V"}]},
                },
            },
        ],
    )
    rec = import_otel_trace(path)
    assert len(rec.steps) == 1
    payload = rec.steps[0].payload
    assert payload.type == "tool_call"
    assert payload.tool == "search"  # type: ignore[union-attr]
    assert payload.response == {"hits": [{"title": "V"}]}  # type: ignore[union-attr]


def test_jsonl_decision_span_becomes_decision(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "agent.plan",
                "spanId": "s1",
                "attributes": {
                    "volo.decision.label": "plan_compute",
                    "volo.decision.chosen": "(a+b)*c",
                    "volo.decision.rationale": "math first",
                },
            },
        ],
    )
    rec = import_otel_trace(path)
    payload = rec.steps[0].payload
    assert payload.type == "decision"
    assert payload.label == "plan_compute"  # type: ignore[union-attr]
    assert payload.chosen == "(a+b)*c"  # type: ignore[union-attr]


def test_parent_relationship_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "llm.completion",
                "spanId": "root",
                "startTimeUnixNano": 1,
                "attributes": {"gen_ai.system": "anthropic", "gen_ai.request.model": "m"},
            },
            {
                "name": "tool.add",
                "spanId": "child",
                "parentSpanId": "root",
                "startTimeUnixNano": 2,
                "attributes": {
                    "tool.name": "add",
                    "tool.input": {"a": 1, "b": 2},
                    "tool.output": {"result": 3},
                },
            },
        ],
    )
    rec = import_otel_trace(path)
    assert len(rec.steps) == 2
    root, child = rec.steps
    assert child.parent_id == root.step_id


def test_spans_are_sorted_by_start_time(tmp_path: Path) -> None:
    """Unordered JSONL must still produce a chronological Recording."""
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "tool.b",
                "spanId": "b",
                "startTimeUnixNano": 200,
                "attributes": {"tool.name": "b", "tool.input": {}, "tool.output": {}},
            },
            {
                "name": "tool.a",
                "spanId": "a",
                "startTimeUnixNano": 100,
                "attributes": {"tool.name": "a", "tool.input": {}, "tool.output": {}},
            },
        ],
    )
    rec = import_otel_trace(path)
    tools = [s.payload.tool for s in rec.steps]  # type: ignore[union-attr]
    assert tools == ["a", "b"]


def test_unknown_spans_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {"name": "http.request", "spanId": "x", "attributes": {}},
            {
                "name": "tool.search",
                "spanId": "y",
                "attributes": {"tool.name": "s", "tool.input": {}, "tool.output": {}},
            },
        ],
    )
    rec = import_otel_trace(path)
    assert len(rec.steps) == 1


# ── otlp json format ─────────────────────────────────────────────────────────


def test_otlp_json_format_with_kv_attributes(tmp_path: Path) -> None:
    path = tmp_path / "trace.json"
    _write_otlp(
        path,
        [
            {
                "name": "llm.completion",
                "spanId": "s",
                "startTimeUnixNano": "1000000",
                "endTimeUnixNano": "2000000",
                "attributes": [
                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                    {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                ],
            },
        ],
        resource_attrs={"service.name": "agent"},
    )
    rec = import_otel_trace(path, framework="langgraph")
    assert len(rec.steps) == 1
    payload = rec.steps[0].payload
    assert payload.provider == "openai"  # type: ignore[union-attr]
    assert payload.model == "gpt-4o"  # type: ignore[union-attr]
    # resource attrs land in RunMeta.extra
    assert rec.agent_meta.extra.get("service.name") == "agent"
    assert rec.agent_meta.framework == "langgraph"


# ── error path ───────────────────────────────────────────────────────────────


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        import_otel_trace("/no/such/file.jsonl")


def test_empty_file_yields_empty_recording(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    rec = import_otel_trace(path)
    assert rec.steps == []


# ── framework wrappers ───────────────────────────────────────────────────────


def test_langgraph_wrapper_passes_framework_label(tmp_path: Path) -> None:
    from volo_langgraph import import_langgraph_otel

    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "tool.x",
                "spanId": "1",
                "attributes": {"tool.name": "x", "tool.input": {}, "tool.output": {}},
            },
        ],
    )
    rec = import_langgraph_otel(path, agent_name="my-graph")
    assert rec.agent_meta.framework == "langgraph"
    assert rec.agent_meta.agent_name == "my-graph"


def test_openai_agents_wrapper_passes_framework_label(tmp_path: Path) -> None:
    from volo_openai_agents import import_openai_agents_otel

    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "tool.x",
                "spanId": "1",
                "attributes": {"tool.name": "x", "tool.input": {}, "tool.output": {}},
            },
        ],
    )
    rec = import_openai_agents_otel(path)
    assert rec.agent_meta.framework == "openai_agents"


def test_crewai_wrapper_passes_framework_label(tmp_path: Path) -> None:
    from volo_crewai import import_crewai_otel

    path = tmp_path / "trace.jsonl"
    _write_jsonl(
        path,
        [
            {
                "name": "tool.x",
                "spanId": "1",
                "attributes": {"tool.name": "x", "tool.input": {}, "tool.output": {}},
            },
        ],
    )
    rec = import_crewai_otel(path)
    assert rec.agent_meta.framework == "crewai"
