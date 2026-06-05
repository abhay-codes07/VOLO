"""Tests for per-recording token/cost roll-ups (cost transparency, bible §11)."""

from __future__ import annotations

from volo_core import ModelCallPayload, Recording


def _rec_with(usages: list[tuple[int | None, float | None]]) -> Recording:
    r = Recording()
    for tokens, cost in usages:
        step = r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={}))
        step.tokens = tokens
        step.cost_usd = cost
    return r


def test_totals_sum_present_values() -> None:
    r = _rec_with([(100, 0.01), (50, 0.005)])
    assert r.total_tokens() == 150
    assert r.total_cost_usd() == 0.015


def test_totals_ignore_none_steps() -> None:
    r = _rec_with([(100, 0.01), (None, None), (25, 0.002)])
    assert r.total_tokens() == 125
    assert r.total_cost_usd() == 0.012


def test_totals_are_none_when_no_usage_recorded() -> None:
    r = _rec_with([(None, None), (None, None)])
    assert r.total_tokens() is None
    assert r.total_cost_usd() is None


def test_empty_recording_has_no_usage() -> None:
    r = Recording()
    assert r.total_tokens() is None
    assert r.total_cost_usd() is None
