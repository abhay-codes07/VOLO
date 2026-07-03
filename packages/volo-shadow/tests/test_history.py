"""SnapshotHistory: append-only JSONL, fleet + per-trace trend series."""

from __future__ import annotations

from pathlib import Path

import pytest

from volo_shadow import DriftFinding, DriftReport, SnapshotHistory


def _snap(d: float, verdict: str = "ship") -> dict:
    return {
        "snapshot_version": 1,
        "entries": {
            "r1": {"aggregate": {"decision_determinism": d}, "verdict": verdict},
            "r2": {"aggregate": {"decision_determinism": 1.0}, "verdict": "ship"},
        },
    }


def test_append_and_entries_roundtrip(tmp_path: Path) -> None:
    hist = SnapshotHistory(tmp_path / "history.jsonl")
    hist.append(_snap(1.0), at="2026-07-03T03:17:00+00:00")
    drift = DriftReport(threshold=0.05)
    drift.findings.append(
        DriftFinding(run_id="r1", dimension="decision_determinism", baseline=1.0, current=0.5)
    )
    hist.append(_snap(0.5), drift=drift, at="2026-07-04T03:17:00+00:00")

    entries = hist.entries()
    assert len(entries) == 2
    assert entries[0]["drift"] is None
    assert entries[1]["drift"]["drifted"] is True


def test_fleet_series_averages_across_traces(tmp_path: Path) -> None:
    hist = SnapshotHistory(tmp_path / "history.jsonl")
    hist.append(_snap(1.0), at="t1")
    hist.append(_snap(0.5), drift=DriftReport(threshold=0.05), at="t2")

    series = hist.fleet_series()
    assert [p["at"] for p in series] == ["t1", "t2"]
    assert series[0]["aggregate"]["decision_determinism"] == pytest.approx(1.0)
    assert series[1]["aggregate"]["decision_determinism"] == pytest.approx(0.75)  # mean(0.5, 1.0)
    assert series[0]["traces"] == 2
    assert series[1]["drifted"] is False  # a report with no findings is quiet


def test_trace_series_follows_one_run(tmp_path: Path) -> None:
    hist = SnapshotHistory(tmp_path / "history.jsonl")
    hist.append(_snap(1.0), at="t1")
    hist.append(_snap(0.5, verdict="no_ship"), at="t2")

    series = hist.trace_series("r1")
    assert [p["aggregate"]["decision_determinism"] for p in series] == [1.0, 0.5]
    assert series[1]["verdict"] == "no_ship"
    assert hist.trace_series("unknown") == []


def test_torn_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    hist = SnapshotHistory(path)
    hist.append(_snap(1.0), at="t1")
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"at": "t2", "snapshot"')  # torn write mid-line
    assert len(hist.entries()) == 1


def test_missing_file_is_empty(tmp_path: Path) -> None:
    hist = SnapshotHistory(tmp_path / "never-written.jsonl")
    assert hist.entries() == [] and hist.fleet_series() == []
