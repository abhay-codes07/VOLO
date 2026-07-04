"""Migration lab — will my agent survive the next model? (newplan M16).

You already recorded your corpus under model **A** (the baseline). Re-record it once under model
**B** (the candidate — the only live cost), then ``run_migration`` pairs the two corpora trace by
trace and, for each pair, answers:

* did the **tool path** change? (model-agnostic — model identity is normalized out)
* did the **final output** change?
* did **faithfulness** move? (heuristic by default, or any ``JudgeProvider``)
* what's the **cost** under each model?

…and rolls the pair outcomes up into a single migration recommendation
(``recommend`` / ``review`` / ``block``) plus a projected cost delta. Everything except the
one re-record pass is deterministic and offline.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, canonical_json
from volo_diff import compute_diff
from volo_models import estimate_cost_usd
from volo_reliability import faithfulness

PairOutcome = Literal["improved", "regressed", "changed", "unchanged"]
Recommendation = Literal["recommend", "review", "block"]

_EPS = 1e-9


def dominant_model(recording: Recording) -> str | None:
    """The most frequent ``provider/model`` across a recording's model calls."""
    counts: dict[str, int] = {}
    for step in recording.steps:
        if step.payload.type == "model_call":
            key = f"{step.payload.provider}/{step.payload.model}"
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda k: counts[k])


def _tool_path(recording: Recording) -> tuple[str, ...]:
    """Model-agnostic trajectory signature: tool names + decisions, model calls normalized.

    Unlike ``volo_reliability.trajectory_shape``, model calls collapse to a bare ``model_call``
    marker so a pure model swap does not, by itself, register as a path change.
    """
    out: list[str] = []
    for step in recording.steps:
        p = step.payload
        if p.type == "model_call":
            out.append("model_call")
        elif p.type == "tool_call":
            out.append(f"tool:{p.tool}")
        else:
            out.append(f"decision:{p.label}")
    return tuple(out)


def _estimated_cost(recording: Recording, model: str | None) -> float:
    """Recorded cost if present, else a token-based estimate (50/50 in/out split)."""
    recorded = recording.total_cost_usd()
    if recorded is not None:
        return recorded
    bare = (model or "").split("/")[-1]
    total = 0.0
    for step in recording.steps:
        if step.payload.type == "model_call" and step.tokens:
            half = step.tokens // 2
            total += estimate_cost_usd(bare, half, step.tokens - half)
    return total


class PairVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    outcome: PairOutcome
    faithfulness_a: float
    faithfulness_b: float
    output_changed: bool
    tool_path_changed: bool
    cost_a_usd: float
    cost_b_usd: float
    first_diverging_step: int | None = None

    @property
    def faithfulness_delta(self) -> float:
        return self.faithfulness_b - self.faithfulness_a


class MigrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_model: str
    to_model: str
    recommendation: Recommendation
    pairs: list[PairVerdict]
    counts: dict[str, int] = Field(default_factory=dict)
    cost_a_usd: float = 0.0
    cost_b_usd: float = 0.0
    unpaired: list[str] = Field(default_factory=list)

    @property
    def cost_delta_usd(self) -> float:
        return self.cost_b_usd - self.cost_a_usd

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def evaluate_pair(
    key: str,
    baseline: Recording,
    candidate: Recording,
    *,
    judge: Any | None = None,
    from_model: str | None = None,
    to_model: str | None = None,
) -> PairVerdict:
    """Score one A/B pair into a ``PairVerdict``."""
    f_a = faithfulness(baseline, judge=judge)
    f_b = faithfulness(candidate, judge=judge)
    output_changed = canonical_json(baseline.final_output) != canonical_json(candidate.final_output)
    tool_path_changed = _tool_path(baseline) != _tool_path(candidate)

    if f_b > f_a + _EPS:
        outcome: PairOutcome = "improved"
    elif f_b < f_a - _EPS:
        outcome = "regressed"
    elif output_changed or tool_path_changed:
        outcome = "changed"
    else:
        outcome = "unchanged"

    diff = compute_diff(baseline, candidate)
    return PairVerdict(
        key=key,
        outcome=outcome,
        faithfulness_a=f_a,
        faithfulness_b=f_b,
        output_changed=output_changed,
        tool_path_changed=tool_path_changed,
        cost_a_usd=_estimated_cost(baseline, from_model),
        cost_b_usd=_estimated_cost(candidate, to_model),
        first_diverging_step=diff.first_diverging_step,
    )


def run_migration(
    pairs: Iterable[tuple[str, Recording, Recording]],
    *,
    from_model: str | None = None,
    to_model: str | None = None,
    judge: Any | None = None,
    unpaired: list[str] | None = None,
) -> MigrationReport:
    """Evaluate every A/B pair and roll up a migration recommendation."""
    pair_list = list(pairs)
    from_label = from_model or (dominant_model(pair_list[0][1]) if pair_list else None) or "model-a"
    to_label = to_model or (dominant_model(pair_list[0][2]) if pair_list else None) or "model-b"

    verdicts = [
        evaluate_pair(k, a, b, judge=judge, from_model=from_label, to_model=to_label)
        for k, a, b in pair_list
    ]
    counts = {o: 0 for o in ("improved", "regressed", "changed", "unchanged")}
    for v in verdicts:
        counts[v.outcome] += 1

    if counts["regressed"]:
        recommendation: Recommendation = "block"
    elif counts["changed"]:
        recommendation = "review"
    else:
        recommendation = "recommend"

    return MigrationReport(
        from_model=from_label,
        to_model=to_label,
        recommendation=recommendation,
        pairs=verdicts,
        counts=counts,
        cost_a_usd=sum(v.cost_a_usd for v in verdicts),
        cost_b_usd=sum(v.cost_b_usd for v in verdicts),
        unpaired=unpaired or [],
    )
