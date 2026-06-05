"""Step-level diff tests (ADR-0007)."""

from __future__ import annotations

from volo_core import (
    DecisionPayload,
    ModelCallPayload,
    Recording,
    ToolCallPayload,
)
from volo_diff import compute_diff, format_diff


def _baseline() -> Recording:
    r = Recording()
    r.add_step(DecisionPayload(label="plan", chosen="x"))
    r.add_step(
        ModelCallPayload(
            provider="echo",
            model="echo-1",
            request={"prompt": "p"},
            response={"text": "ok"},
        ),
    )
    r.add_step(ToolCallPayload(tool="add", request={"a": 2, "b": 3}, response={"result": 5}))
    r.add_step(ToolCallPayload(tool="multiply", request={"a": 5, "b": 4}, response={"result": 20}))
    r.final_output = {"answer": 20}
    return r


def test_diff_identical_recordings_reports_no_divergence() -> None:
    r1 = _baseline()
    r2 = _baseline()
    d = compute_diff(r1, r2)
    assert d.first_diverging_step is None
    assert d.summary == "no trajectory divergence"
    assert all(sd.kind == "same" for sd in d.aligned_steps)


def test_diff_detects_changed_payload() -> None:
    r1 = _baseline()
    r2 = _baseline()
    r2.steps[2].payload.response = {"result": 99}  # add returns 99 instead of 5
    d = compute_diff(r1, r2)
    assert d.first_diverging_step == 2
    sd = d.aligned_steps[2]
    assert sd.kind == "changed"
    assert "response" in sd.changed_keys


def test_diff_detects_added_step() -> None:
    r1 = _baseline()
    r2 = _baseline()
    r2.add_step(ToolCallPayload(tool="extra", request={}, response={}))
    d = compute_diff(r1, r2)
    assert d.first_diverging_step is not None
    assert any(sd.kind == "added" for sd in d.aligned_steps)


def test_diff_detects_removed_step() -> None:
    r1 = _baseline()
    r2 = _baseline()
    r2.steps.pop(2)  # remove the add step
    d = compute_diff(r1, r2)
    assert any(sd.kind == "removed" for sd in d.aligned_steps)


def test_format_diff_is_human_readable() -> None:
    r1 = _baseline()
    r2 = _baseline()
    r2.steps[2].payload.response = {"result": 99}
    text = format_diff(compute_diff(r1, r2))
    assert "diff" in text
    assert "first divergence" in text


def test_diff_json_round_trips() -> None:
    r1 = _baseline()
    r2 = _baseline()
    r2.steps[2].payload.response = {"result": 99}
    d = compute_diff(r1, r2)
    blob = d.to_json()
    from volo_diff import Diff

    d2 = Diff.model_validate_json(blob)
    assert d2.first_diverging_step == d.first_diverging_step
