"""Hexagonal-architecture ports. Every other package depends on these, not on each other."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from volo_core.recording import Recording


class Clock(ABC):
    @abstractmethod
    def now_iso(self) -> str: ...


class SystemClock(Clock):
    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat(timespec="microseconds")


class FrozenClock(Clock):
    """Deterministic clock that advances by a fixed step. Used in replay / CI."""

    def __init__(self, start_iso: str, step_seconds: float = 0.001) -> None:
        self._t = datetime.fromisoformat(start_iso)
        self._step = step_seconds

    def now_iso(self) -> str:
        from datetime import timedelta

        out = self._t.isoformat(timespec="microseconds")
        self._t = self._t + timedelta(seconds=self._step)
        return out


class RandomSource(ABC):
    @abstractmethod
    def seed(self, value: int) -> None: ...

    @abstractmethod
    def random(self) -> float: ...


class SeededRandom(RandomSource):
    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def seed(self, value: int) -> None:
        self._rng = random.Random(value)

    def random(self) -> float:
        return self._rng.random()


class ModelProvider(ABC):
    """A model backend — Ollama, OpenAI, Anthropic, or a `ReplayProvider` in CI."""

    @abstractmethod
    def complete(self, request: dict[str, Any]) -> dict[str, Any]: ...


class ToolRegistry(ABC):
    """A bag of callable tools the agent can invoke."""

    @abstractmethod
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]: ...


class SimulatedEnvironment(ABC):
    """The runtime the replayer / runner hands to an agent in place of the real world.

    Tier-1 implementations satisfy this by replaying from a recording cache; Tier-2 implementations
    additionally synthesize responses for un-recorded inputs.
    """

    @abstractmethod
    def model_provider(self, provider: str = "unknown", model: str = "unknown") -> ModelProvider:
        """Return a ``ModelProvider`` that answers for the (provider, model) pair.

        The pair is required because the same Recording may contain calls to multiple models
        under different provider names; the simulator must demux them.
        """

    @abstractmethod
    def tool_registry(self) -> ToolRegistry: ...

    @classmethod
    @abstractmethod
    def from_recording(cls, recording: Recording) -> SimulatedEnvironment: ...
