"""Two agents for the long-horizon rig: one that rots, one that doesn't.

``drifting`` accumulates the rig's ``memory`` and, once it has piled up past a threshold, "loses
the thread" and returns an ungrounded answer — the classic context-rot failure that only shows up
over a long session. ``stable`` ignores memory and answers from the tool every episode, so it
holds steady no matter how many episodes run.
"""

from __future__ import annotations

from typing import Any

from volo_core import get_active_environment

_ROT_THRESHOLD = 3


def _search() -> dict[str, Any]:
    env = get_active_environment()
    if env is None:
        raise RuntimeError("no active Volo environment")
    return env.tool_registry().call("search", {"q": "volo"})


def drifting(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """VULNERABLE to drift: after enough accumulated memory, its answer goes ungrounded."""
    result = _search()
    memory = (payload or {}).get("memory", [])
    if len(memory) >= _ROT_THRESHOLD:
        # context rot — the true value is result["hits"], but the agent has lost track
        return {"hits": 99999}
    return {"hits": result["hits"]}


def stable(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Holds steady: answers from the tool every episode, ignores accumulated memory."""
    return {"hits": _search()["hits"]}
