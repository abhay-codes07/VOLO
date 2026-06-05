"""Cost transparency in the ReliabilityReport (bible §11)."""

from __future__ import annotations

from volo_core import ModelCallPayload, Recording
from volo_reliability import aggregate_runs, compose_report


def _baseline_with_cost() -> Recording:
    r = Recording()
    s1 = r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={}))
    s1.tokens, s1.cost_usd = 800, 0.012
    s2 = r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={}))
    s2.tokens, s2.cost_usd = 200, 0.004
    return r


def _report(baseline: Recording, **kw: float):
    sub = aggregate_runs([baseline], scenario_op="x", failure_class="y", seed=0)
    return compose_report(baseline, [sub], **kw)


# ── report population ──────────────────────────────────────────────────────────


def test_report_carries_recorded_usage_from_baseline() -> None:
    report = _report(_baseline_with_cost())
    assert report.recorded_tokens == 1000
    assert report.recorded_cost_usd == 0.016
    assert report.simulated_cost_usd == 0.0


def test_saved_cost_is_recorded_minus_simulated() -> None:
    report = _report(_baseline_with_cost(), simulated_cost_usd=0.001)
    assert report.saved_cost_usd == 0.015


def test_usage_is_none_when_baseline_has_no_cost() -> None:
    report = _report(Recording())
    assert report.recorded_tokens is None
    assert report.recorded_cost_usd is None
    assert report.saved_cost_usd is None


def test_report_round_trips_with_new_fields() -> None:
    report = _report(_baseline_with_cost(), simulated_cost_usd=0.002)
    again = type(report).from_json(report.to_json())
    assert again.recorded_cost_usd == 0.016
    assert again.simulated_cost_usd == 0.002


def test_old_report_without_cost_fields_still_loads() -> None:
    """Backward compat: reports written before the cost fields existed must still parse."""
    blob = (
        '{"baseline_run_id":"r","aggregate":{"trajectory_determinism":1.0,'
        '"decision_determinism":1.0,"faithfulness":1.0,"consistency_under_repetition":1.0},'
        '"verdict":"ship","scenarios":[]}'
    )
    from volo_reliability import ReliabilityReport

    report = ReliabilityReport.from_json(blob)
    assert report.recorded_cost_usd is None
    assert report.simulated_cost_usd == 0.0
