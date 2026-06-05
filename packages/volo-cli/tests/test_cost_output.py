"""Tests for the CLI cost/token formatter (bible §11 — visible cost in CLI output)."""

from __future__ import annotations

from volo_cli.commands._cost import cost_cap_breach, cost_lines
from volo_core import ModelCallPayload, Recording
from volo_reliability import aggregate_runs, compose_report


def _report(baseline: Recording, **kw: float):
    sub = aggregate_runs([baseline], scenario_op="x", failure_class="y", seed=0)
    return compose_report(baseline, [sub], **kw)


def _baseline_with_cost() -> Recording:
    r = Recording()
    s = r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={}))
    s.tokens, s.cost_usd = 1000, 0.016
    return r


def test_cost_lines_render_full_summary() -> None:
    text = "\n".join(cost_lines(_report(_baseline_with_cost())))
    assert "cost:" in text
    assert "1,000 tok" in text
    assert "$0.0160" in text  # recorded (live run)
    assert "$0.0000" in text  # simulated (this run)
    assert "saved" in text


def test_cost_lines_neutral_when_no_usage() -> None:
    assert cost_lines(_report(Recording())) == [
        "cost: no token/cost usage recorded in this trace",
    ]


# ── --max-cost-usd hard cap ──────────────────────────────────────────────────


def test_no_cap_never_breaches() -> None:
    assert cost_cap_breach(_report(_baseline_with_cost()), None) is None


def test_tier1_run_never_breaches_cap() -> None:
    # simulated_cost_usd is $0 under Tier-1 replay, so even a $0 cap is fine.
    assert cost_cap_breach(_report(_baseline_with_cost()), 0.0) is None


def test_cap_breached_when_simulated_spend_exceeds() -> None:
    report = _report(_baseline_with_cost(), simulated_cost_usd=0.05)
    msg = cost_cap_breach(report, 0.01)
    assert msg is not None
    assert "cost cap exceeded" in msg


def test_cap_not_breached_when_within() -> None:
    report = _report(_baseline_with_cost(), simulated_cost_usd=0.005)
    assert cost_cap_breach(report, 0.01) is None
