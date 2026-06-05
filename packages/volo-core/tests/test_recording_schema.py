"""Tests for the Recording schema. ADR-0003."""

from __future__ import annotations

import pytest

from volo_core import (
    RECORDING_SCHEMA_VERSION,
    DecisionPayload,
    ModelCallPayload,
    Recording,
    RunMeta,
    Step,
    ToolCallPayload,
    ToolSpec,
)


def test_schema_version_constant() -> None:
    assert RECORDING_SCHEMA_VERSION == "1.0.0"


def test_recording_defaults_are_valid() -> None:
    r = Recording()
    assert r.recording_schema_version == "1.0.0"
    assert r.steps == []
    assert r.redaction_applied is False
    assert r.run_id  # not empty


def test_add_step_appends_and_returns() -> None:
    r = Recording()
    s = r.add_step(ModelCallPayload(provider="anthropic", model="haiku", request={"prompt": "hi"}))
    assert isinstance(s, Step)
    assert r.steps == [s]
    assert s.type == "model_call"


def test_step_branching_via_parent_id() -> None:
    r = Recording()
    a = r.add_step(DecisionPayload(label="route", options=["A", "B"], chosen="A"))
    b = r.add_step(
        ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": []}),
        parent_id=a.step_id,
    )
    assert b.parent_id == a.step_id
    assert {s.type for s in r.steps} == {"decision", "tool_call"}


def test_json_round_trip_preserves_payloads() -> None:
    r = Recording(
        agent_meta=RunMeta(framework="langgraph", agent_name="demo", seed=42),
        tool_specs=[ToolSpec(name="search", description="web search")],
    )
    r.add_step(ModelCallPayload(provider="ollama", model="llama3.2:3b", request={"prompt": "hi"}))
    r.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": []}))
    r.add_step(DecisionPayload(label="terminate", chosen="yes"))
    r.final_output = {"answer": "ok"}

    blob = r.to_json()
    r2 = Recording.from_json(blob)

    assert r2.run_id == r.run_id
    assert [s.type for s in r2.steps] == ["model_call", "tool_call", "decision"]
    assert r2.final_output == {"answer": "ok"}
    assert r2.agent_meta.framework == "langgraph"
    assert r2.agent_meta.seed == 42
    assert r2.tool_specs[0].name == "search"


def test_rejects_unknown_schema_version() -> None:
    blob = '{"recording_schema_version": "9.9.9"}'
    with pytest.raises(ValueError, match="Unsupported recording_schema_version"):
        Recording.from_json(blob)


def test_run_meta_uses_alias_for_model_config() -> None:
    """`model_config` is a reserved Pydantic attribute — we expose it via alias on RunMeta."""
    meta = RunMeta.model_validate({"framework": "x", "model_config": {"temperature": 0.0}})
    assert meta.model_config_ == {"temperature": 0.0}
    blob = meta.model_dump_json(by_alias=True)
    assert '"model_config"' in blob


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValueError):
        Recording.model_validate({"recording_schema_version": "1.0.0", "bogus_field": 1})
