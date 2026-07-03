"""Drift sentinel core — replay the corpus nightly, compare the reliability surface (M13).

``snapshot`` replays every banked trace against the *current* agent build and records each
entry's aggregate reliability dimensions + verdict. ``compare`` diffs two snapshots: any
dimension that dropped by more than ``threshold``, or any ship → no_ship verdict flip, is a
**drift finding** — users hear about a regression before their users do.

Snapshots are plain JSON so CI can commit/cache them; the alert is the process exit code
(``volo shadow check`` exits 3 on drift).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from volo_runner import OrchestratorConfig, orchestrate
from volo_shadow.corpus import CorpusBank

SNAPSHOT_VERSION = 1


@dataclass(frozen=True)
class DriftFinding:
    run_id: str
    dimension: str  # a reliability dimension, or "verdict" for a ship→no_ship flip
    baseline: float
    current: float

    @property
    def delta(self) -> float:
        return self.current - self.baseline


@dataclass
class DriftReport:
    threshold: float
    findings: list[DriftFinding] = field(default_factory=list)
    new_runs: list[str] = field(default_factory=list)  # in current but not baseline
    missing_runs: list[str] = field(default_factory=list)  # in baseline but not current

    @property
    def drifted(self) -> bool:
        return bool(self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drifted": self.drifted,
            "threshold": self.threshold,
            "findings": [
                {
                    "run_id": f.run_id,
                    "dimension": f.dimension,
                    "baseline": f.baseline,
                    "current": f.current,
                    "delta": f.delta,
                }
                for f in self.findings
            ],
            "new_runs": self.new_runs,
            "missing_runs": self.missing_runs,
        }


def snapshot(
    bank: CorpusBank,
    agent: Callable[..., Any] | str,
    *,
    n_runs: int = 2,
    seed: int = 0,
    fail_under: float = 0.9,
    judge: Any | None = None,
) -> dict[str, Any]:
    """Replay every corpus entry through the full scenario suite; return the surface snapshot."""
    entries: dict[str, Any] = {}
    for entry, recording in bank.load_all():
        config = OrchestratorConfig(n_runs=n_runs, seed=seed, fail_under=fail_under, judge=judge)
        report = orchestrate(recording, agent, config=config)
        entries[entry.run_id] = {
            "aggregate": dict(report.aggregate),
            "verdict": report.verdict,
            "source": entry.source,
        }
    return {"snapshot_version": SNAPSHOT_VERSION, "entries": entries}


def compare(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    threshold: float = 0.05,
) -> DriftReport:
    """Diff two snapshots. A finding = dimension dropped > threshold, or verdict flipped."""
    report = DriftReport(threshold=threshold)
    base_entries: dict[str, Any] = baseline.get("entries", {})
    cur_entries: dict[str, Any] = current.get("entries", {})

    report.new_runs = sorted(set(cur_entries) - set(base_entries))
    report.missing_runs = sorted(set(base_entries) - set(cur_entries))

    for run_id in sorted(set(base_entries) & set(cur_entries)):
        base, cur = base_entries[run_id], cur_entries[run_id]
        for dimension, base_value in (base.get("aggregate") or {}).items():
            cur_value = (cur.get("aggregate") or {}).get(dimension)
            if not isinstance(base_value, int | float) or not isinstance(cur_value, int | float):
                continue
            if cur_value < base_value - threshold:
                report.findings.append(
                    DriftFinding(
                        run_id=run_id,
                        dimension=str(dimension),
                        baseline=float(base_value),
                        current=float(cur_value),
                    )
                )
        if base.get("verdict") == "ship" and cur.get("verdict") == "no_ship":
            report.findings.append(
                DriftFinding(run_id=run_id, dimension="verdict", baseline=1.0, current=0.0)
            )
    return report
