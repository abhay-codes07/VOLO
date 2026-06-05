"""A 4-step deterministic "calculator agent" with zero LLM dependencies.

Trajectory shape (for testing the simulator + scenarios + reliability):

    decision   -> "plan_compute"
    model_call -> "echo/echo-1"   (planner — returns the plan verbatim)
    tool_call  -> "add"           (a+b)
    tool_call  -> "multiply"      ((a+b) * c)
    model_call -> "echo/echo-1"   (summarizer — emits final phrasing)

Final output: ``{"answer": ((a+b)*c)}``.
"""

from __future__ import annotations

from typing import Any

from volo_core import DecisionPayload, get_active_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import ModelProviderProxy, ToolRegistryProxy


class _DeterministicModel(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": request.get("prompt", ""), "stop_reason": "end_turn"}


class _MathTools(ToolRegistry):
    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        if tool == "add":
            return {"result": int(request["a"]) + int(request["b"])}
        if tool == "multiply":
            return {"result": int(request["a"]) * int(request["b"])}
        raise KeyError(f"unknown tool: {tool!r}")


def _make_proxies() -> tuple[ModelProviderProxy, ToolRegistryProxy]:
    model = ModelProviderProxy(
        _DeterministicModel(),
        provider_name="echo",
        model_name="echo-1",
    )
    tools = ToolRegistryProxy(_MathTools())
    return model, tools


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    a = int(payload.get("a", 0))
    b = int(payload.get("b", 0))
    c = int(payload.get("c", 1))

    model, tools = _make_proxies()

    rec = get_active_recorder()
    if rec is not None:
        rec.record_step(DecisionPayload(label="plan_compute", chosen=f"({a}+{b})*{c}"))

    model.complete({"prompt": f"plan: compute ({a}+{b})*{c}"})
    sum_ = tools.call("add", {"a": a, "b": b})["result"]
    prod = tools.call("multiply", {"a": sum_, "b": c})["result"]
    model.complete({"prompt": f"summary: answer is {prod}"})

    return {"answer": prod}
