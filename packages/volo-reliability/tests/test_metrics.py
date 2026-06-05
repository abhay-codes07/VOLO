"""Tests for the four reliability metrics (ADR-0006)."""

from __future__ import annotations

from volo_core import (
    ModelCallPayload,
    Recording,
    ToolCallPayload,
)
from volo_reliability import (
    METRIC_NAMES,
    aggregate_runs,
    compose_report,
    consistency_under_repetition,
    decision_determinism,
    faithfulness,
    trajectory_determinism,
    trajectory_shape,
)


def _calc_run(answer: int = 20) -> Recording:
    r = Recording()
    r.add_step(ToolCallPayload(tool="add", request={"a": 2, "b": 3}, response={"result": 5}))
    r.add_step(
        ToolCallPayload(tool="multiply", request={"a": 5, "b": 4}, response={"result": answer})
    )
    r.add_step(
        ModelCallPayload(
            provider="echo", model="echo-1", request={"prompt": "x"}, response={"text": str(answer)}
        )
    )
    r.final_output = {"answer": answer}
    return r


def test_trajectory_shape_is_value_robust() -> None:
    a = _calc_run(20)
    b = _calc_run(999)  # same shape, different values
    assert trajectory_shape(a) == trajectory_shape(b)


def test_trajectory_determinism_perfect_when_shapes_match() -> None:
    runs = [_calc_run(20) for _ in range(5)]
    assert trajectory_determinism(runs) == 1.0


def test_decision_determinism_drops_with_variation() -> None:
    runs = [_calc_run(20), _calc_run(20), _calc_run(20), _calc_run(21), _calc_run(22)]
    # 3 out of 5 share the modal output.
    assert decision_determinism(runs) == 0.6


def test_consistency_under_repetition_perfect_when_identical() -> None:
    runs = [_calc_run(20) for _ in range(4)]
    assert consistency_under_repetition(runs) == 1.0


def test_consistency_drops_with_diverging_runs() -> None:
    runs = [_calc_run(i) for i in range(5)]  # all unique outputs
    # 5 unique / 5 → dispersion 0.8 → score 0.2
    assert abs(consistency_under_repetition(runs) - 0.2) < 1e-9


def test_faithfulness_grounded_for_calc() -> None:
    assert faithfulness(_calc_run(20)) == 1.0


def test_faithfulness_zero_when_output_not_in_evidence() -> None:
    r = _calc_run(20)
    r.final_output = {"answer": 999}  # 999 isn't anywhere in the trajectory
    assert faithfulness(r) == 0.0


def test_aggregate_runs_metrics_all_present() -> None:
    runs = [_calc_run(20) for _ in range(3)]
    report = aggregate_runs(
        runs,
        scenario_op="drop_tool_result",
        failure_class="resilience",
        seed=0,
    )
    assert set(report.metrics.keys()) == set(METRIC_NAMES)
    assert all(0.0 <= v <= 1.0 for v in report.metrics.values())


def test_compose_report_ships_on_perfect() -> None:
    baseline = _calc_run(20)
    sub = aggregate_runs(
        [_calc_run(20) for _ in range(3)],
        scenario_op="op",
        failure_class="x",
        seed=0,
    )
    rep = compose_report(baseline, [sub])
    assert rep.verdict == "ship"
    assert all(v == 1.0 for v in rep.aggregate.values())


def test_compose_report_blocks_on_zero_metric() -> None:
    baseline = _calc_run(20)
    bad = _calc_run(
        999
    )  # faithfulness will be 0 on this single-run scenario? No, 999 also derivable from numbers.
    # Force faithfulness to 0 by making the answer un-derivable.
    bad.final_output = {"answer": "totally fabricated unseen string"}
    sub = aggregate_runs(
        [bad],
        scenario_op="op",
        failure_class="x",
        seed=0,
    )
    rep = compose_report(baseline, [sub])
    assert rep.verdict == "no_ship"


def test_report_round_trips_through_json() -> None:
    baseline = _calc_run(20)
    sub = aggregate_runs(
        [_calc_run(20) for _ in range(2)],
        scenario_op="op",
        failure_class="x",
        seed=0,
    )
    rep = compose_report(baseline, [sub])
    blob = rep.to_json()
    rep2 = type(rep).from_json(blob)
    assert rep2.verdict == rep.verdict
    assert rep2.aggregate == rep.aggregate
