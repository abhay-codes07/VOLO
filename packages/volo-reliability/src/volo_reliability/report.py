"""ReliabilityReport schema + aggregation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording
from volo_reliability.metrics import (
    consistency_under_repetition,
    decision_determinism,
    faithfulness,
    trajectory_determinism,
)

METRIC_NAMES: tuple[str, ...] = (
    "trajectory_determinism",
    "decision_determinism",
    "faithfulness",
    "consistency_under_repetition",
)

Verdict = Literal["ship", "no_ship"]


def _p5(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    # Lower-tail 5th percentile via linear interpolation; with 1 value this is just that value.
    if len(s) == 1:
        return s[0]
    idx = 0.05 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


class ScenarioReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_op: str
    failure_class: str
    seed: int
    n_runs: int
    metrics: dict[str, float]
    histogram: dict[str, int] = Field(default_factory=dict)  # canonical_json(final_output) -> count
    applicable: bool = True
    notes: str | None = None


class ReliabilityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    agent_name: str | None = None
    fail_under: float = 0.9
    aggregate: dict[str, float]
    verdict: Verdict
    scenarios: list[ScenarioReport]
    # Cost transparency (bible §11). ``recorded_*`` is what the agent cost when captured live;
    # ``simulated_cost_usd`` is what this reliability run cost — $0 under Tier-1 replay, and
    # non-zero only if an opt-in frontier judge/synthesizer was used.
    recorded_tokens: int | None = None
    recorded_cost_usd: float | None = None
    simulated_cost_usd: float = 0.0

    @property
    def saved_cost_usd(self) -> float | None:
        """API spend avoided by replaying instead of re-running live, or ``None`` if unknown."""
        if self.recorded_cost_usd is None:
            return None
        return max(0.0, self.recorded_cost_usd - self.simulated_cost_usd)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, raw: str) -> ReliabilityReport:
        return cls.model_validate_json(raw)


def aggregate_runs(
    runs: list[Recording],
    *,
    scenario_op: str,
    failure_class: str,
    seed: int,
    applicable: bool = True,
    judge: Any | None = None,
) -> ScenarioReport:
    """Compute the four metrics for a list of runs of the same scenario.

    ``judge`` is an optional ``JudgeProvider`` for faithfulness scoring; ``None`` (default)
    uses the zero-cost heuristic.
    """
    from collections import Counter

    from volo_core import canonical_json

    if not runs:
        return ScenarioReport(
            scenario_op=scenario_op,
            failure_class=failure_class,
            seed=seed,
            n_runs=0,
            metrics=dict.fromkeys(METRIC_NAMES, 0.0),
            applicable=applicable,
            notes="no runs",
        )

    histogram = Counter(canonical_json(r.final_output) for r in runs)
    faith = sum(faithfulness(r, judge=judge) for r in runs) / len(runs)
    return ScenarioReport(
        scenario_op=scenario_op,
        failure_class=failure_class,
        seed=seed,
        n_runs=len(runs),
        metrics={
            "trajectory_determinism": trajectory_determinism(runs),
            "decision_determinism": decision_determinism(runs),
            "faithfulness": faith,
            "consistency_under_repetition": consistency_under_repetition(runs),
        },
        histogram=dict(histogram),
        applicable=applicable,
    )


def compose_report(
    baseline: Recording,
    scenario_reports: list[ScenarioReport],
    *,
    fail_under: float = 0.9,
    aggregator: str = "p5",
    simulated_cost_usd: float = 0.0,
) -> ReliabilityReport:
    """Compose per-scenario reports into a single report + verdict.

    ``simulated_cost_usd`` is the real API spend this run incurred (0 under Tier-1 replay;
    non-zero only if an opt-in frontier judge/synthesizer was invoked).
    """
    fn: Callable[[list[float]], float] = {
        "p5": _p5,
        "mean": lambda xs: sum(xs) / len(xs) if xs else 0.0,
        "median": lambda xs: sorted(xs)[len(xs) // 2] if xs else 0.0,
    }[aggregator]

    aggregate: dict[str, float] = {}
    for name in METRIC_NAMES:
        scores = [r.metrics.get(name, 0.0) for r in scenario_reports if r.applicable]
        aggregate[name] = fn(scores)

    any_zero = any(
        r.metrics.get(name, 0.0) == 0.0
        for r in scenario_reports
        if r.applicable
        for name in METRIC_NAMES
    )
    passes_floor = all(aggregate[n] >= fail_under for n in METRIC_NAMES)
    verdict: Verdict = "ship" if passes_floor and not any_zero else "no_ship"

    return ReliabilityReport(
        baseline_run_id=baseline.run_id,
        agent_name=baseline.agent_meta.agent_name,
        fail_under=fail_under,
        aggregate=aggregate,
        verdict=verdict,
        scenarios=scenario_reports,
        recorded_tokens=baseline.total_tokens(),
        recorded_cost_usd=baseline.total_cost_usd(),
        simulated_cost_usd=simulated_cost_usd,
    )
