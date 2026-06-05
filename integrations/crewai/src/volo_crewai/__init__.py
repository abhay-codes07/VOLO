"""volo-crewai — wrap a CrewAI Crew and import its OTel traces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_core import Recording, get_active_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_core.recording import DecisionPayload
from volo_sdk import ModelProviderProxy, ToolRegistryProxy, import_otel_trace


def wrap(
    crew: Any,
    *,
    model: ModelProvider | None = None,
    tools: ToolRegistry | None = None,
) -> Any:
    """Wrap a CrewAI ``Crew`` so each agent's tool/model calls are captured.

    CrewAI's crew exposes ``.agents`` (each with ``.llm`` and ``.tools``) and
    ``.kickoff(...)``. We:

    1. Replace each agent's ``llm`` with a ``ModelProviderProxy`` around the supplied
       ``model`` (or leave in place if ``model is None``).
    2. Wrap the tool list with our ``ToolRegistryProxy``.
    3. Patch ``crew.kickoff`` to emit a ``decision`` step on each agent handoff so the
       Volo trajectory keeps the crew structure visible.
    """
    if hasattr(crew, "agents"):
        for agent in crew.agents:
            if model is not None and hasattr(agent, "llm"):
                agent.llm = ModelProviderProxy(
                    model,
                    provider_name="crewai",
                    model_name=getattr(model, "model", "default"),
                )
            if tools is not None and hasattr(agent, "tools"):
                agent.tools = ToolRegistryProxy(tools)
    _wrap_kickoff(crew)
    return crew


def _wrap_kickoff(crew: Any) -> None:
    fn = getattr(crew, "kickoff", None)
    if not callable(fn) or getattr(fn, "_volo_wrapped", False):
        return

    def kickoff(*args: Any, **kwargs: Any) -> Any:
        rec = get_active_recorder()
        if rec is not None:
            rec.record_step(DecisionPayload(label="crew_kickoff", chosen="run"))
        return fn(*args, **kwargs)

    kickoff._volo_wrapped = True  # type: ignore[attr-defined]
    kickoff.__name__ = "kickoff"
    crew.kickoff = kickoff


def import_crewai_otel(
    path: str | Path,
    *,
    agent_name: str | None = None,
) -> Recording:
    """Import a CrewAI OTel trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="crewai")


__all__ = ["import_crewai_otel", "wrap"]
