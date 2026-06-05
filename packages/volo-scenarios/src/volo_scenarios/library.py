"""The default scenario library — one seeded instance of each operator."""

from __future__ import annotations

from volo_core import Recording
from volo_scenarios.base import Scenario, ScenarioOp
from volo_scenarios.operators import (
    AmbiguousUserTurn,
    CorruptField,
    DropToolResult,
    InjectLatency,
    LongHorizonRepeat,
    PromptInjection,
    ReorderSteps,
)

_DEFAULT_OPS: tuple[type[ScenarioOp], ...] = (
    DropToolResult,
    CorruptField,
    InjectLatency,
    AmbiguousUserTurn,
    PromptInjection,
    ReorderSteps,
    LongHorizonRepeat,
)


def default_library(seed: int = 0) -> list[ScenarioOp]:
    """Return one instance of each default operator, all sharing the same base seed."""
    return [cls(seed=seed + i) for i, cls in enumerate(_DEFAULT_OPS)]


def generate_default_scenarios(
    recording: Recording,
    *,
    seed: int = 0,
) -> list[tuple[Scenario, Recording]]:
    """Materialize the default library against a baseline Recording.

    Returns a list of (Scenario metadata, mutated Recording) pairs ready for the runner.
    """
    out: list[tuple[Scenario, Recording]] = []
    for op in default_library(seed=seed):
        mutated = op.apply(recording)
        out.append((op.scenario(), mutated))
    return out
