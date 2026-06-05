"""SSE live-run streaming (bible §9.6).

A simple in-process registry of run-id → asyncio.Queue. Producers (the runner, or a future
ingestion endpoint) push step events; ``GET /runs/{run_id}/stream`` consumes them as SSE.

Two modes:

* **Replay mode** — when a run has already finished, ``stream_run`` reads the persisted
  ``Recording`` once and emits each step as an SSE event, terminated by ``event: done``.
* **Live mode** — when a producer is registered for the run, ``stream_run`` proxies the
  queue. Multiple subscribers fan out via independent queues.

This module is intentionally **dependency-light** — no Redis, no kafka — so the OSS path
runs locally without infrastructure.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from volo_core import Recording

# Producer registry: run_id → set of subscriber queues.
_subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}


async def publish(run_id: str, event: dict[str, Any]) -> None:
    """Fan-out an event to every subscriber of ``run_id``. Safe when nobody's listening."""
    queues = _subscribers.get(run_id) or set()
    for q in list(queues):
        await q.put(event)


def _open_subscription(run_id: str) -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=512)
    _subscribers.setdefault(run_id, set()).add(q)
    return q


def _close_subscription(run_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
    if run_id in _subscribers:
        _subscribers[run_id].discard(q)
        if not _subscribers[run_id]:
            del _subscribers[run_id]


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def stream_recording(recording: Recording) -> AsyncIterator[str]:
    """Emit each step of a persisted recording as an SSE event."""
    yield _sse("start", {"run_id": recording.run_id, "n_steps": len(recording.steps)})
    for idx, step in enumerate(recording.steps):
        payload = step.payload.model_dump(mode="python")
        yield _sse(
            "step",
            {
                "index": idx,
                "step_id": step.step_id,
                "parent_id": step.parent_id,
                "latency_ms": step.latency_ms,
                "payload": payload,
            },
        )
        # Yield to the event loop so the response actually flushes between events.
        await asyncio.sleep(0)
    yield _sse("done", {"run_id": recording.run_id, "final_output": recording.final_output})


async def stream_live(run_id: str, *, idle_timeout_s: float = 30.0) -> AsyncIterator[str]:
    """Subscribe to live events for ``run_id``. Times out after ``idle_timeout_s`` idle."""
    q = _open_subscription(run_id)
    try:
        yield _sse("start", {"run_id": run_id, "mode": "live"})
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=idle_timeout_s)
            except TimeoutError:
                yield _sse("idle", {"run_id": run_id})
                return
            if event.get("__terminal__"):
                yield _sse("done", event)
                return
            yield _sse("step", event)
    finally:
        _close_subscription(run_id, q)


__all__ = ["publish", "stream_live", "stream_recording"]
