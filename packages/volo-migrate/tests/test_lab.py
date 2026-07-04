"""Migration lab: pair outcomes, cost delta, and the roll-up recommendation."""

from __future__ import annotations

from typing import Any

from volo_core import ModelCallPayload, Recording, ToolCallPayload
from volo_migrate import dominant_model, evaluate_pair, run_migration


def _rec(
    *, answer: Any, model: str = "m-a", tool_response: dict[str, Any] | None = None, tokens: int = 0
) -> Recording:
    rec = Recording()
    rec.add_step(
        ToolCallPayload(
            tool="search", request={"q": "x"}, response=tool_response or {"hits": 3, "note": "ok"}
        )
    )
    step = rec.add_step(
        ModelCallPayload(provider="p", model=model, request={"prompt": "sum"}, response={"t": "y"})
    )
    if tokens:
        step.tokens = tokens
    rec.final_output = answer
    return rec


def test_dominant_model() -> None:
    assert dominant_model(_rec(answer={"a": 1}, model="claude-haiku-4-5")) == "p/claude-haiku-4-5"
    assert dominant_model(Recording()) is None


def test_unchanged_pair() -> None:
    a = _rec(answer={"hits": 3})
    b = _rec(answer={"hits": 3}, model="m-b")
    v = evaluate_pair("t", a, b)
    assert v.outcome == "unchanged"
    assert not v.output_changed and not v.tool_path_changed


def test_changed_output_same_faithfulness_is_changed() -> None:
    # both outputs grounded (bool is always grounded), but they differ → "changed"
    a = _rec(answer={"ok": True})
    b = _rec(answer={"ok": False}, model="m-b")
    v = evaluate_pair("t", a, b)
    assert v.output_changed is True
    assert v.faithfulness_a == v.faithfulness_b
    assert v.outcome == "changed"


def test_regressed_when_candidate_hallucinates() -> None:
    a = _rec(answer={"hits": 3})  # grounded → faithful
    b = _rec(answer={"hits": 99999}, model="m-b")  # ungrounded number → unfaithful
    v = evaluate_pair("t", a, b)
    assert v.faithfulness_a > v.faithfulness_b
    assert v.outcome == "regressed"


def test_improved_when_candidate_becomes_grounded() -> None:
    a = _rec(answer={"hits": 88888})  # ungrounded → unfaithful
    b = _rec(answer={"hits": 3}, model="m-b")  # grounded → faithful
    v = evaluate_pair("t", a, b)
    assert v.outcome == "improved"


def test_run_migration_blocks_on_any_regression() -> None:
    pairs = [
        ("keep", _rec(answer={"hits": 3}), _rec(answer={"hits": 3}, model="m-b")),
        ("break", _rec(answer={"hits": 3}), _rec(answer={"hits": 77777}, model="m-b")),
    ]
    report = run_migration(pairs, from_model="m-a", to_model="m-b")
    assert report.recommendation == "block"
    assert report.counts["regressed"] == 1 and report.counts["unchanged"] == 1


def test_run_migration_review_on_change_only() -> None:
    pairs = [("t", _rec(answer={"ok": True}), _rec(answer={"ok": False}, model="m-b"))]
    report = run_migration(pairs)
    assert report.recommendation == "review"


def test_run_migration_recommend_when_clean() -> None:
    pairs = [("t", _rec(answer={"hits": 3}), _rec(answer={"hits": 3}, model="m-b"))]
    report = run_migration(pairs)
    assert report.recommendation == "recommend"


def test_cost_delta_from_tokens_and_pricing() -> None:
    # baseline: a paid model with tokens; candidate: a free local model
    a = _rec(answer={"hits": 3}, model="claude-opus-4-7", tokens=2000)
    b = _rec(answer={"hits": 3}, model="llama3.2:3b", tokens=2000)
    report = run_migration([("t", a, b)], from_model="claude-opus-4-7", to_model="llama3.2:3b")
    assert report.cost_a_usd > 0.0  # opus priced
    assert report.cost_b_usd == 0.0  # local free
    assert report.cost_delta_usd < 0.0  # migration saves money


def test_report_json_roundtrip() -> None:
    from volo_migrate import MigrationReport

    report = run_migration([("t", _rec(answer={"hits": 3}), _rec(answer={"hits": 3}, model="m-b"))])
    restored = MigrationReport.model_validate_json(report.to_json())
    assert restored.recommendation == report.recommendation
    assert restored.pairs[0].key == "t"
