"""Drift sentinel: a stable agent stays quiet; a seeded regression trips the alert (M13)."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import pytest

from volo_core import ModelCallPayload, Recording, ToolCallPayload
from volo_shadow import CorpusBank, compare, snapshot

_counter = itertools.count()


def _stable_agent(payload: Any = None) -> dict[str, Any]:
    return {"answer": "one hit"}


def _regressed_agent(payload: Any = None) -> dict[str, Any]:
    return {"answer": f"draft-{next(_counter)}"}  # nondeterministic → determinism collapses


def _bank(tmp_path: Path) -> CorpusBank:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 1}))
    rec.add_step(
        ModelCallPayload(
            provider="ollama",
            model="llama3.2:3b",
            request={"prompt": "summarize"},
            response={"text": "one hit"},
        )
    )
    rec.final_output = {"answer": "one hit"}
    bank = CorpusBank(tmp_path / "corpus")
    assert bank.add(rec) is not None
    return bank


def test_stable_agent_shows_no_drift(tmp_path: Path) -> None:
    bank = _bank(tmp_path)
    baseline = snapshot(bank, _stable_agent, n_runs=2)
    tonight = snapshot(bank, _stable_agent, n_runs=2)
    report = compare(baseline, tonight)
    assert not report.drifted
    assert report.new_runs == [] and report.missing_runs == []


def test_seeded_regression_trips_the_alert(tmp_path: Path) -> None:
    """The M13 acceptance test."""
    bank = _bank(tmp_path)
    baseline = snapshot(bank, _stable_agent, n_runs=2)
    tonight = snapshot(bank, _regressed_agent, n_runs=2)
    report = compare(baseline, tonight)
    assert report.drifted
    dims = {f.dimension for f in report.findings}
    assert dims  # at least one reliability dimension collapsed
    assert all(f.delta < 0 for f in report.findings if f.dimension != "verdict")


def test_compare_threshold_and_membership() -> None:
    base = {"entries": {"r1": {"aggregate": {"d": 0.90}, "verdict": "ship"}}}
    ok = {"entries": {"r1": {"aggregate": {"d": 0.87}, "verdict": "ship"}}}
    bad = {"entries": {"r1": {"aggregate": {"d": 0.80}, "verdict": "ship"}}}

    assert not compare(base, ok, threshold=0.05).drifted  # 0.03 drop is inside tolerance
    report = compare(base, bad, threshold=0.05)
    assert report.drifted and report.findings[0].delta == pytest.approx(-0.10)

    moved = compare(base, {"entries": {"r2": {"aggregate": {}, "verdict": "ship"}}})
    assert moved.new_runs == ["r2"] and moved.missing_runs == ["r1"]


def test_verdict_flip_is_a_finding_even_without_metric_drop() -> None:
    base = {"entries": {"r1": {"aggregate": {"d": 0.95}, "verdict": "ship"}}}
    cur = {"entries": {"r1": {"aggregate": {"d": 0.95}, "verdict": "no_ship"}}}
    report = compare(base, cur)
    assert report.drifted
    assert report.findings[0].dimension == "verdict"
