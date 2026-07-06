"""Drive an agent against a persona and report the conversation + goal verdict (newplan M17)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, current_environment
from volo_personas.environment import DEFAULT_USER_TOOLS, PersonaEnvironment
from volo_personas.persona import Persona, goal_satisfied


class ConversationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: str
    goal: str
    turns: int
    transcript: list[dict[str, str]] = Field(default_factory=list)
    final_output: Any = None
    goal_met: bool = False
    error: str | None = None

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def drive_persona(
    agent: Callable[..., Any],
    persona: Persona,
    *,
    recording: Recording | None = None,
    agent_input: dict[str, Any] | None = None,
    user_tools: frozenset[str] = DEFAULT_USER_TOOLS,
) -> ConversationReport:
    """Run ``agent`` against a ``PersonaEnvironment``; return the conversation + goal verdict."""
    env = PersonaEnvironment(persona, recording=recording, user_tools=user_tools)
    error: str | None = None
    final: Any = None
    with current_environment(env):
        try:
            final = agent(agent_input) if agent_input is not None else agent()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    return ConversationReport(
        persona=persona.name,
        goal=persona.goal,
        turns=env.user.turns,
        transcript=env.user.transcript,
        final_output=final,
        goal_met=error is None and goal_satisfied(final, persona),
        error=error,
    )
