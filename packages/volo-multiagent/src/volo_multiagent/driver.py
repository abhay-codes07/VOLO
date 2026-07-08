"""Drive an orchestrator against simulated counterparties and produce a system verdict (M32)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, current_environment
from volo_multiagent.environment import Counterparty, MultiAgentEnvironment
from volo_personas import goal_satisfied
from volo_personas.persona import Persona

SystemVerdict = Literal["healthy", "broken"]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frm: str = "orchestrator"
    to: str
    message: str
    reply: str | None = None
    unknown: bool = False


class SystemReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orchestrator: str | None = None
    verdict: SystemVerdict
    counterparties: list[str] = Field(default_factory=list)
    reached: list[str] = Field(default_factory=list)  # counterparties actually delegated to
    unreached: list[str] = Field(default_factory=list)  # declared but never called
    unknown_agents: list[str] = Field(default_factory=list)  # delegated to a non-existent agent
    delegations: int = 0
    messages: list[Message] = Field(default_factory=list)
    final_output: Any = None
    goal_met: bool = True
    error: str | None = None

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def run_multiagent(
    orchestrator: Callable[..., Any],
    counterparties: list[Counterparty],
    *,
    recording: Recording | None = None,
    agent_input: dict[str, Any] | None = None,
    expected: list[str] | None = None,
) -> SystemReport:
    """Run ``orchestrator`` against simulated ``counterparties``; return the system report."""
    env = MultiAgentEnvironment(counterparties, recording=recording)
    error: str | None = None
    final: Any = None
    with current_environment(env):
        try:
            final = orchestrator(agent_input) if agent_input is not None else orchestrator()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    names = [c.name for c in counterparties]
    reached = sorted(env.state.by_agent())
    unknown = sorted({c.to for c in env.state.calls if c.unknown})
    unreached = sorted(set(names) - set(reached))
    goal_met = error is None and goal_satisfied(
        final, Persona(name="_goal", expected=expected or [])
    )

    healthy = error is None and not unknown and goal_met
    return SystemReport(
        orchestrator=_name_of(orchestrator),
        verdict="healthy" if healthy else "broken",
        counterparties=names,
        reached=reached,
        unreached=unreached,
        unknown_agents=unknown,
        delegations=len(env.state.calls),
        messages=[
            Message(to=c.to, message=c.message, reply=c.reply, unknown=c.unknown)
            for c in env.state.calls
        ],
        final_output=final,
        goal_met=goal_met,
        error=error,
    )


def _name_of(fn: Callable[..., Any]) -> str | None:
    mod = getattr(fn, "__module__", None)
    name = getattr(fn, "__name__", None)
    return f"{mod}:{name}" if mod and name else name


def load_counterparties(data: dict[str, Any]) -> list[Counterparty]:
    """Build counterparties from ``{name: persona_dict}`` (or ``{"counterparties": {...}}``)."""
    raw = data.get("counterparties", data)
    if not isinstance(raw, dict):
        raise ValueError("counterparties must be an object of name -> persona")
    out: list[Counterparty] = []
    for name, persona_dict in raw.items():
        pdata = dict(persona_dict or {})
        pdata.setdefault("name", str(name))
        out.append(Counterparty(name=str(name), persona=Persona.from_dict(pdata)))
    return out


def load_counterparties_json(text: str) -> list[Counterparty]:
    return load_counterparties(json.loads(text))
