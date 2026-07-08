"""A tiny orchestrator that delegates to sub-agents — the M32 multi-agent demo target.

Given a topic, it delegates to a ``researcher`` (to gather facts) then a ``writer`` (to draft),
via the ``delegate`` tool, and combines their replies. Run against simulated counterparties
(``volo multiagent run``), the sub-agents answer deterministically from personas, so a whole
crew/graph becomes a reproducible system test.
"""

from __future__ import annotations

from typing import Any

from volo_core import get_active_environment


def _delegate(to: str, message: str) -> str:
    env = get_active_environment()
    if env is None:
        raise RuntimeError("no active Volo environment")
    reply = env.tool_registry().call("delegate", {"to": to, "message": message})
    return str(reply.get("reply", ""))


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    topic = (payload or {}).get("topic", "volo")
    findings = _delegate("researcher", f"research: {topic}")
    draft = _delegate("writer", f"write about: {findings}")
    return {"topic": topic, "findings": findings, "draft": draft}
