"""Capture proxies — see ADR-0004.

A ``ModelProviderProxy`` wraps any ``ModelProvider`` and emits a ``ModelCallPayload`` to the
active recorder on each ``.complete()`` call. A ``ToolRegistryProxy`` does the same for
``ToolRegistry.call()``.

Resolution order per call (see ADR-0004):
1. If a ``SimulatedEnvironment`` is active (replay/sim mode), delegate to **its** provider /
   registry — this is how Tier-1 / Tier-2 swap in.
2. Otherwise, delegate to the ``inner`` passed at construction time (record / live mode).
3. Regardless, if a ``Recorder`` is active, append a step.
"""

from __future__ import annotations

import time
from typing import Any

from volo_core import (
    ModelCallPayload,
    ToolCallPayload,
    get_active_environment,
    get_active_recorder,
)
from volo_core.interfaces import ModelProvider, ToolRegistry


class ModelProviderProxy(ModelProvider):
    def __init__(self, inner: ModelProvider, *, provider_name: str, model_name: str) -> None:
        self._inner = inner
        self._provider_name = provider_name
        self._model_name = model_name

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        env = get_active_environment()
        rec = get_active_recorder()
        started = time.perf_counter()
        response: dict[str, Any]
        try:
            if env is not None:
                # In sim mode, the env's provider serves the response — it needs the same identity.
                provider = env.model_provider(self._provider_name, self._model_name)
                response = provider.complete(dict(request))
            else:
                response = self._inner.complete(dict(request))
        finally:
            latency_ms = (time.perf_counter() - started) * 1000.0
        if rec is not None:
            rec.record_step(
                ModelCallPayload(
                    provider=self._provider_name,
                    model=self._model_name,
                    request=dict(request),
                    response=dict(response),
                ),
            )
            rec.recording.steps[-1].latency_ms = latency_ms
        return response


class ToolRegistryProxy(ToolRegistry):
    def __init__(self, inner: ToolRegistry) -> None:
        self._inner = inner

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        env = get_active_environment()
        rec = get_active_recorder()
        started = time.perf_counter()
        response: dict[str, Any]
        try:
            if env is not None:
                response = env.tool_registry().call(tool, dict(request))
            else:
                response = self._inner.call(tool, dict(request))
        finally:
            latency_ms = (time.perf_counter() - started) * 1000.0
        if rec is not None:
            rec.record_step(
                ToolCallPayload(tool=tool, request=dict(request), response=dict(response)),
            )
            rec.recording.steps[-1].latency_ms = latency_ms
        return response
