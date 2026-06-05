"""Tier-1 Replayer — deterministic cache-replay (bible §9.2 / ADR-0003).

Builds a ``SimulatedEnvironment`` from a ``Recording``. Every ``model_call`` and ``tool_call``
step in the recording becomes an entry in the replay cache keyed on the canonical request.
``ModelProvider.complete`` / ``ToolRegistry.call`` then serve hits from the cache; misses raise
``ReplayMiss`` (subclass of ``LookupError``) — Tier-2 will synthesize for misses, but Tier-1
refuses to hallucinate.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from volo_core import Recording, cache_key
from volo_core.interfaces import ModelProvider, SimulatedEnvironment, ToolRegistry


class ReplayMiss(LookupError):
    """Raised when a Tier-1 replayer is asked about an input it never saw at record time."""


def _model_key(provider: str, model: str, request: dict[str, Any]) -> str:
    return cache_key("model_call", provider, model, request)


def _tool_key(tool: str, request: dict[str, Any]) -> str:
    return cache_key("tool_call", tool, request)


class ReplayModelProvider(ModelProvider):
    """Serves model responses from a recorded cache."""

    def __init__(self, cache: dict[str, deque[dict[str, Any]]]) -> None:
        self._cache = cache

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        provider = str(request.pop("__provider__", "unknown"))
        model = str(request.pop("__model__", "unknown"))
        key = _model_key(provider, model, request)
        bucket = self._cache.get(key)
        if not bucket:
            raise ReplayMiss(
                f"no recorded model_call for provider={provider!r} model={model!r}; "
                f"key={key} — Tier-1 will not synthesize (Tier-2 will).",
            )
        return dict(bucket.popleft())


class _KeyedModelProvider(ModelProvider):
    """A ``ModelProvider`` that knows its own provider/model identity.

    The agent code calls ``proxy.complete(request)`` (no provider/model fields). At record time
    the proxy supplies provider/model from its constructor; at replay time we want the SAME
    identity-aware behavior. Wrapping the raw ``ReplayModelProvider`` in this adapter lets the
    Tier-1 replayer be transparently swapped in.
    """

    def __init__(self, inner: ReplayModelProvider, provider: str, model: str) -> None:
        self._inner = inner
        self._provider = provider
        self._model = model

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = {"__provider__": self._provider, "__model__": self._model, **request}
        return self._inner.complete(payload)


class ReplayToolRegistry(ToolRegistry):
    """Serves tool responses from a recorded cache."""

    def __init__(self, cache: dict[str, deque[dict[str, Any]]]) -> None:
        self._cache = cache

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        key = _tool_key(tool, request)
        bucket = self._cache.get(key)
        if not bucket:
            raise ReplayMiss(
                f"no recorded tool_call for tool={tool!r}; key={key} — "
                f"Tier-1 will not synthesize (Tier-2 will).",
            )
        return dict(bucket.popleft())


class Tier1Replayer(SimulatedEnvironment):
    """Deterministic cache-replay environment built from a Recording."""

    def __init__(self, recording: Recording) -> None:
        self._recording = recording
        self._model_cache: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        self._tool_cache: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        for step in recording.steps:
            p = step.payload
            if p.type == "model_call" and p.response is not None:
                self._model_cache[_model_key(p.provider, p.model, p.request)].append(p.response)
            elif p.type == "tool_call" and p.response is not None:
                self._tool_cache[_tool_key(p.tool, p.request)].append(p.response)

    @classmethod
    def from_recording(cls, recording: Recording) -> Tier1Replayer:
        return cls(recording)

    def model_provider(self, provider: str = "unknown", model: str = "unknown") -> ModelProvider:
        return _KeyedModelProvider(ReplayModelProvider(self._model_cache), provider, model)

    def tool_registry(self) -> ToolRegistry:
        return ReplayToolRegistry(self._tool_cache)

    # ---- introspection ----

    @property
    def recording(self) -> Recording:
        return self._recording

    def stats(self) -> dict[str, int]:
        return {
            "model_entries": sum(len(b) for b in self._model_cache.values()),
            "tool_entries": sum(len(b) for b in self._tool_cache.values()),
            "model_keys": len(self._model_cache),
            "tool_keys": len(self._tool_cache),
        }
