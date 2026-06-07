"""Tests for the Markdown reliability summary (PR comments / job summary)."""

from __future__ import annotations

from volo_cli.commands._summary import report_markdown
from volo_core import ModelCallPayload, Recording
from volo_reliability import aggregate_runs, compose_report


def _report(baseline: Recording, **kw: float):
    sub = aggregate_runs([baseline], scenario_op="x", failure_class="y", seed=0)
    return compose_report(baseline, [sub], **kw)


def test_markdown_has_verdict_and_metric_table() -> None:
    md = report_markdown(_report(Recording()))
    assert "Volo reliability" in md
    assert ("SHIP" in md) or ("NO-SHIP" in md)
    assert "| Metric | Score |" in md
    assert "Trajectory determinism" in md
    assert "Faithfulness" in md


def test_markdown_zero_cost_line_when_no_usage() -> None:
    md = report_markdown(_report(Recording()))
    assert "$0" in md


def test_markdown_shows_recorded_and_saved_cost() -> None:
    r = Recording()
    s = r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={}))
    s.tokens, s.cost_usd = 1000, 0.02
    md = report_markdown(_report(r, simulated_cost_usd=0.0))
    assert "recorded (live) $0.0200" in md
    assert "saved" in md


def test_markdown_passes_and_fails_marks() -> None:
    # A grounded recording scores faithfulness 1.0 (✅); the table should render check marks.
    md = report_markdown(_report(Recording()))
    assert "✅" in md or "❌" in md
