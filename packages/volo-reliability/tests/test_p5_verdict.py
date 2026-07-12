"""Pin the p5 verdict aggregator: percentile math + the tolerate-one-but-not-two semantics.

These lock down the headline ship/no_ship output. Before this, every reliability test used all-1.0
or a forced 0.0 (caught by the separate any_zero guard), so swapping _p5 for max/mean passed.
"""

from __future__ import annotations

from volo_core import Recording
from volo_reliability.report import ScenarioReport, _p5, compose_report


def test_p5_percentile_math() -> None:
    # lower-tail 5th percentile via linear interpolation
    assert abs(_p5([0.0, 0.5, 1.0]) - 0.05) < 1e-9
    assert _p5([0.4]) == 0.4  # single value
    assert _p5([]) == 0.0  # empty -> 0.0 (fail-safe)
    # not max/mean: a lone low value dominates the lower tail relative to the mean
    assert _p5([0.0] + [1.0] * 3) < 0.5


def _scenarios(faithfulness: list[float]) -> list[ScenarioReport]:
    # every other metric perfect; only faithfulness varies, so it alone drives the verdict
    return [
        ScenarioReport(
            scenario_op=f"op{i}",
            failure_class="c",
            seed=i,
            n_runs=1,
            metrics={
                "trajectory_determinism": 1.0,
                "decision_determinism": 1.0,
                "faithfulness": f,
                "consistency_under_repetition": 1.0,
            },
        )
        for i, f in enumerate(faithfulness)
    ]


def test_verdict_tolerates_one_sub_floor_scenario_but_not_two() -> None:
    baseline = Recording()
    # 0.5 is sub-floor (fail_under=0.9) but non-zero, so it dodges the any_zero guard and the
    # verdict rests purely on the p5 aggregate.
    one = compose_report(baseline, _scenarios([1.0] * 20 + [0.5]))
    two = compose_report(baseline, _scenarios([1.0] * 20 + [0.5, 0.5]))
    assert one.verdict == "ship"  # p5 tolerates the worst ~5%
    assert two.verdict == "no_ship"  # two sub-floor scenarios pull p5 below the floor
    assert one.aggregate["faithfulness"] == 1.0
    assert two.aggregate["faithfulness"] < 0.9


def test_empty_and_non_applicable_compose_to_no_ship() -> None:
    baseline = Recording()
    assert compose_report(baseline, []).verdict == "no_ship"
    non_applicable = [
        s.model_copy(update={"applicable": False}) for s in _scenarios([1.0, 1.0, 1.0])
    ]
    report = compose_report(baseline, non_applicable)
    assert report.verdict == "no_ship"  # nothing evaluated -> fail-safe, not a silent ship
    assert all(v == 0.0 for v in report.aggregate.values())
