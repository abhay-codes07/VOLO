"""Tests for the seven scenario operators (ADR-0005)."""

from __future__ import annotations

from volo_core import (
    DecisionPayload,
    ModelCallPayload,
    Recording,
    ToolCallPayload,
)
from volo_scenarios import (
    AmbiguousUserTurn,
    CorruptField,
    DropToolResult,
    InjectLatency,
    LongHorizonRepeat,
    PromptInjection,
    ReorderSteps,
    generate_default_scenarios,
)


def _make_calc_recording() -> Recording:
    r = Recording()
    r.add_step(DecisionPayload(label="plan", chosen="x"))
    r.add_step(
        ModelCallPayload(
            provider="echo",
            model="echo-1",
            request={"prompt": "plan: compute (2+3)*4"},
            response={"text": "ok"},
        ),
    )
    parent = r.steps[-1].step_id
    r.add_step(
        ToolCallPayload(tool="add", request={"a": 2, "b": 3}, response={"result": 5}),
        parent_id=parent,
    )
    r.add_step(
        ToolCallPayload(tool="multiply", request={"a": 5, "b": 4}, response={"result": 20}),
        parent_id=parent,
    )
    r.add_step(
        ModelCallPayload(
            provider="echo",
            model="echo-1",
            request={"prompt": "summary"},
            response={"text": "20"},
        ),
    )
    r.final_output = {"answer": 20}
    return r


def test_drop_tool_result_blanks_one_response() -> None:
    out = DropToolResult(seed=0).apply(_make_calc_recording())
    blanks = [s for s in out.steps if s.payload.type == "tool_call" and s.payload.response == {}]
    assert len(blanks) == 1


def test_corrupt_field_changes_one_leaf() -> None:
    base = _make_calc_recording()
    out = CorruptField(seed=0).apply(base)
    base_responses = [s.payload.response for s in base.steps if s.payload.type == "tool_call"]
    out_responses = [s.payload.response for s in out.steps if s.payload.type == "tool_call"]
    assert base_responses != out_responses


def test_inject_latency_multiplies_one_step() -> None:
    base = _make_calc_recording()
    for step in base.steps:
        step.latency_ms = 10.0
    out = InjectLatency(seed=0, factor=50.0).apply(base)
    latencies = [s.latency_ms for s in out.steps if s.latency_ms is not None]
    assert any(lat >= 500.0 for lat in latencies), latencies


def test_ambiguous_user_turn_replaces_first_prompt() -> None:
    out = AmbiguousUserTurn(seed=0).apply(_make_calc_recording())
    first_model = next(s for s in out.steps if s.payload.type == "model_call")
    assert first_model.payload.request["prompt"] == "do the thing"


def test_prompt_injection_embeds_hostile_string() -> None:
    out = PromptInjection(seed=0).apply(_make_calc_recording())
    tool_responses = [s.payload.response for s in out.steps if s.payload.type == "tool_call"]
    assert any("IGNORE PREVIOUS INSTRUCTIONS" in str(r) for r in tool_responses)


def test_reorder_steps_swaps_adjacent_sibling_tool_calls() -> None:
    base = _make_calc_recording()
    out = ReorderSteps(seed=0).apply(base)
    tools = [s for s in out.steps if s.payload.type == "tool_call"]
    base_tools = [s for s in base.steps if s.payload.type == "tool_call"]
    assert tools[0].payload.tool != base_tools[0].payload.tool


def test_long_horizon_repeat_extends_tool_runs() -> None:
    base = _make_calc_recording()
    out = LongHorizonRepeat(seed=0, n=3).apply(base)
    assert len(out.steps) > len(base.steps)
    n_tools = sum(1 for s in out.steps if s.payload.type == "tool_call")
    assert n_tools == 3 * sum(1 for s in base.steps if s.payload.type == "tool_call")


def test_operators_are_deterministic_under_seed() -> None:
    base = _make_calc_recording()
    a = CorruptField(seed=42).apply(base)
    b = CorruptField(seed=42).apply(base)
    # Compare just the steps — Recording defaults like run_id are stable across clones because
    # _clone goes through model_dump/model_validate which preserves explicit field values.
    assert [s.payload.model_dump() for s in a.steps] == [s.payload.model_dump() for s in b.steps]


def test_operators_do_not_mutate_input() -> None:
    base = _make_calc_recording()
    before = base.to_json()
    for op_cls in (
        DropToolResult,
        CorruptField,
        InjectLatency,
        AmbiguousUserTurn,
        PromptInjection,
        ReorderSteps,
        LongHorizonRepeat,
    ):
        op_cls(seed=0).apply(base)
    assert base.to_json() == before


def test_default_library_yields_seven_scenarios() -> None:
    pairs = generate_default_scenarios(_make_calc_recording(), seed=0)
    assert len(pairs) == 7
    names = [sc.op_name for sc, _ in pairs]
    assert set(names) == {
        "drop_tool_result",
        "corrupt_field",
        "inject_latency",
        "ambiguous_user_turn",
        "prompt_injection",
        "reorder_steps",
        "long_horizon_repeat",
    }


def test_operators_skip_cleanly_when_inapplicable() -> None:
    empty = Recording()
    # None of the tool-targeting operators should crash on an empty recording.
    for op_cls in (DropToolResult, CorruptField, PromptInjection, ReorderSteps, LongHorizonRepeat):
        out = op_cls(seed=0).apply(empty)
        assert isinstance(out, Recording)
