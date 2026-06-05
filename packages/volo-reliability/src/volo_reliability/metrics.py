"""The four reliability metrics (ADR-0006)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from volo_core import Recording, canonical_json


def trajectory_shape(recording: Recording) -> tuple[tuple[str, str], ...]:
    """The "shape" of a trajectory — robust to value-level noise."""
    out: list[tuple[str, str]] = []
    for step in recording.steps:
        p = step.payload
        if p.type == "model_call":
            out.append(("model_call", f"{p.provider}/{p.model}"))
        elif p.type == "tool_call":
            out.append(("tool_call", p.tool))
        else:
            out.append(("decision", p.label))
    return tuple(out)


def _mode_fraction(items: list[Any]) -> float:
    if not items:
        return 0.0
    counts = Counter(items)
    return counts.most_common(1)[0][1] / len(items)


def trajectory_determinism(recordings: list[Recording]) -> float:
    """Fraction of runs whose trajectory shape matches the modal shape."""
    return _mode_fraction([trajectory_shape(r) for r in recordings])


def decision_determinism(recordings: list[Recording]) -> float:
    """Fraction of runs whose final_output matches the modal output (canonical JSON)."""
    return _mode_fraction([canonical_json(r.final_output) for r in recordings])


def consistency_under_repetition(recordings: list[Recording]) -> float:
    """``1 - (unique_outputs / N)``, in [0, 1]."""
    if not recordings:
        return 0.0
    unique = len({canonical_json(r.final_output) for r in recordings})
    return max(0.0, 1.0 - (unique - 1) / max(1, len(recordings)))


def _collect_evidence(rec: Recording) -> tuple[set[str], set[float]]:
    """Pull strings + numbers from every tool/model response into evidence sets."""
    strings: set[str] = set()
    numbers: set[float] = set()

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            strings.add(v)
        elif isinstance(v, bool):
            return
        elif isinstance(v, (int, float)):
            numbers.add(float(v))

    for step in rec.steps:
        p = step.payload
        if p.type in ("model_call", "tool_call"):
            walk(p.response or {})
    return strings, numbers


def _is_grounded(value: Any, strings: set[str], numbers: set[float]) -> bool:
    if isinstance(value, dict):
        return all(_is_grounded(v, strings, numbers) for v in value.values())
    if isinstance(value, list):
        return all(_is_grounded(v, strings, numbers) for v in value)
    if isinstance(value, str):
        return any(value in candidate or candidate in value for candidate in strings)
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        target = float(value)
        if target in numbers:
            return True
        # Allow derivations from sums and products of two evidence numbers — covers calc_agent.
        nums = list(numbers)
        for i, a in enumerate(nums):
            for b in nums[i:]:
                if abs(a + b - target) < 1e-9 or abs(a * b - target) < 1e-9:
                    return True
        return False
    return value is None


def faithfulness(recording: Recording, *, judge: Any | None = None) -> float:
    """Score whether ``recording.final_output`` is grounded in recorded evidence, in [0, 1].

    ``judge`` is an optional ``JudgeProvider`` (``volo_reliability.judge``). When ``None``
    (default), uses the pure-Python heuristic — zero cost, deterministic, 0/1 per run.
    When provided, the judge's score is returned in [0, 1] (LLM-style continuous).
    """
    if judge is not None:
        return float(judge.score(recording))
    strings, numbers = _collect_evidence(recording)
    return 1.0 if _is_grounded(recording.final_output, strings, numbers) else 0.0
