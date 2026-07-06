"""Persona environment — a simulated user as a first-class environment actor (newplan M17).

``PersonaEnvironment`` wraps any inner ``SimulatedEnvironment`` (Tier-1 replay by default) and
intercepts the agent's "ask the user" tool calls, routing them to a ``SimulatedUser`` while every
other tool/model call passes through to the inner sim. So a multi-turn agent runs unchanged — it
just gets deterministic, persona-driven answers to its questions, and Volo captures the whole
conversation for inspection and goal-checking.

The same mechanism models any counterparty (a sub-agent, another agent): give it a persona and
point the agent's delegation tool at it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from volo_core import Recording
from volo_core.interfaces import ModelProvider, SimulatedEnvironment, ToolRegistry
from volo_personas.persona import Persona
from volo_simulator import Tier1Replayer

# Tool names an agent might use to talk to its counterparty. The question is read from the first
# of these request keys that is present.
DEFAULT_USER_TOOLS: frozenset[str] = frozenset({"ask_user", "user", "clarify", "ask"})
_QUESTION_KEYS: tuple[str, ...] = ("question", "prompt", "text", "message", "q")


@dataclass
class SimulatedUser:
    """A persona plus its running conversation state."""

    persona: Persona
    transcript: list[dict[str, str]] = field(default_factory=list)
    _fallbacks: int = 0

    def ask(self, question: str) -> str:
        answer = self.persona.answer(question, script_turn=self._fallbacks)
        # Advance the script pointer only when a fallback (script/default) was used, not a fact.
        q = question.lower()
        matched_fact = any(k.lower() in q for k in self.persona.facts)
        if not matched_fact:
            self._fallbacks += 1
        self.transcript.append({"question": question, "answer": answer})
        return answer

    @property
    def turns(self) -> int:
        return len(self.transcript)


class _PersonaToolRegistry(ToolRegistry):
    def __init__(self, inner: ToolRegistry, user: SimulatedUser, tools: frozenset[str]) -> None:
        self._inner = inner
        self._user = user
        self._tools = tools

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        if tool in self._tools:
            question = next(
                (str(request[k]) for k in _QUESTION_KEYS if k in request),
                "",
            )
            return {"answer": self._user.ask(question)}
        return self._inner.call(tool, request)


class PersonaEnvironment(SimulatedEnvironment):
    """A simulated environment whose "ask the user" calls are answered by a persona."""

    def __init__(
        self,
        persona: Persona,
        *,
        recording: Recording | None = None,
        user_tools: frozenset[str] = DEFAULT_USER_TOOLS,
    ) -> None:
        self._inner: SimulatedEnvironment = Tier1Replayer.from_recording(recording or Recording())
        self.user = SimulatedUser(persona=persona)
        self._user_tools = user_tools

    @classmethod
    def from_recording(cls, recording: Recording) -> PersonaEnvironment:
        """Required by the interface; uses a neutral persona (prefer the full constructor)."""
        return cls(Persona(name="neutral"), recording=recording)

    def model_provider(self, provider: str = "unknown", model: str = "unknown") -> ModelProvider:
        return self._inner.model_provider(provider, model)

    def tool_registry(self) -> ToolRegistry:
        return _PersonaToolRegistry(self._inner.tool_registry(), self.user, self._user_tools)
