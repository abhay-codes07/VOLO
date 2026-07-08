"""Multi-agent environment — simulate an orchestrator's sub-agents as counterparties (M32).

An orchestrator (a LangGraph graph, a CrewAI crew, a hand-rolled router) delegates to sub-agents.
``MultiAgentEnvironment`` wraps the simulator and intercepts the orchestrator's **delegation** tool
calls — ``delegate`` / ``call_agent`` / ``handoff`` with a ``to`` + ``message``, or an
``agent.<name>`` tool — routing each to the named counterparty (a persona-backed responder, M17)
and recording the inter-agent message. Every other tool/model call passes through to Tier-1
replay, so the orchestrator runs unchanged and Volo captures the whole system interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from volo_core import Recording
from volo_core.interfaces import ModelProvider, SimulatedEnvironment, ToolRegistry
from volo_personas import Persona
from volo_simulator import Tier1Replayer

DEFAULT_DELEGATE_TOOLS: frozenset[str] = frozenset({"delegate", "call_agent", "handoff"})
AGENT_TOOL_PREFIX = "agent."
_TARGET_KEYS: tuple[str, ...] = ("to", "agent", "target", "name")
_MESSAGE_KEYS: tuple[str, ...] = ("message", "task", "query", "input", "prompt")


@dataclass(frozen=True)
class Counterparty:
    """A simulated sub-agent: a name plus the persona that answers its delegations."""

    name: str
    persona: Persona


@dataclass
class DelegationCall:
    to: str
    message: str
    reply: str | None = None
    unknown: bool = False


@dataclass
class MultiAgentState:
    calls: list[DelegationCall] = field(default_factory=list)

    def by_agent(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.calls:
            out[c.to] = out.get(c.to, 0) + 1
        return out


def _extract(request: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for k in keys:
        if k in request:
            return str(request[k])
    return default


class _RoutingToolRegistry(ToolRegistry):
    def __init__(
        self,
        inner: ToolRegistry,
        counterparties: dict[str, Counterparty],
        state: MultiAgentState,
        delegate_tools: frozenset[str],
    ) -> None:
        self._inner = inner
        self._cp = counterparties
        self._state = state
        self._delegate_tools = delegate_tools
        self._turns: dict[str, int] = {}

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        target, message = self._route(tool, request)
        if target is None:
            return self._inner.call(tool, request)
        cp = self._cp.get(target)
        if cp is None:
            self._state.calls.append(DelegationCall(to=target, message=message, unknown=True))
            return {"__unknown_agent__": target}
        turn = self._turns.get(target, 0)
        reply = cp.persona.answer(message, script_turn=turn)
        self._turns[target] = turn + 1
        self._state.calls.append(DelegationCall(to=target, message=message, reply=reply))
        return {"reply": reply, "agent": target}

    def _route(self, tool: str, request: dict[str, Any]) -> tuple[str | None, str]:
        if tool in self._delegate_tools:
            return _extract(request, _TARGET_KEYS), _extract(request, _MESSAGE_KEYS)
        if tool.startswith(AGENT_TOOL_PREFIX):
            return tool[len(AGENT_TOOL_PREFIX) :], _extract(request, _MESSAGE_KEYS)
        return None, ""


class MultiAgentEnvironment(SimulatedEnvironment):
    """A simulated environment that answers an orchestrator's delegations from counterparties."""

    def __init__(
        self,
        counterparties: list[Counterparty],
        *,
        recording: Recording | None = None,
        delegate_tools: frozenset[str] = DEFAULT_DELEGATE_TOOLS,
    ) -> None:
        self._inner: SimulatedEnvironment = Tier1Replayer.from_recording(recording or Recording())
        self._cp = {c.name: c for c in counterparties}
        self._delegate_tools = delegate_tools
        self.state = MultiAgentState()

    @classmethod
    def from_recording(cls, recording: Recording) -> MultiAgentEnvironment:
        return cls([], recording=recording)

    def model_provider(self, provider: str = "unknown", model: str = "unknown") -> ModelProvider:
        return self._inner.model_provider(provider, model)

    def tool_registry(self) -> ToolRegistry:
        return _RoutingToolRegistry(
            self._inner.tool_registry(), self._cp, self.state, self._delegate_tools
        )
