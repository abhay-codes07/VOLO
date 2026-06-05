"""Scenario base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from volo_core import Recording


@dataclass(frozen=True)
class Scenario:
    """A reproducible adversarial scenario.

    The combination of (operator name, seed, params) uniquely identifies the mutation. The runner
    persists this triple alongside the resulting ``ReliabilityReport`` so any failure is
    reproducible.
    """

    op_name: str
    failure_class: str
    seed: int = 0
    params: dict[str, Any] = field(default_factory=dict)
    label: str = ""

    def display(self) -> str:
        return self.label or f"{self.op_name}@seed{self.seed}"


class ScenarioOp(ABC):
    """A pure function from one ``Recording`` to a mutated ``Recording``."""

    name: str = ""
    failure_class: str = ""

    def __init__(self, *, seed: int = 0, **params: Any) -> None:
        self.seed = seed
        self.params = dict(params)

    @abstractmethod
    def apply(self, recording: Recording) -> Recording: ...

    def scenario(self, label: str = "") -> Scenario:
        return Scenario(
            op_name=self.name,
            failure_class=self.failure_class,
            seed=self.seed,
            params=dict(self.params),
            label=label,
        )

    def _clone(self, recording: Recording) -> Recording:
        """Return a deep clone of the Recording so apply() stays pure."""
        return Recording.model_validate(recording.model_dump(mode="python", by_alias=True))
