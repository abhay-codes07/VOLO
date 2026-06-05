"""Same trajectory shape as calc_agent, but with an off-by-one bug at the multiply step."""

from __future__ import annotations

from typing import Any

from volo_core import DecisionPayload, get_active_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import ModelProviderProxy, ToolRegistryProxy


class _DeterministicModel(ModelProvider):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"text": request.get("prompt", ""), "stop_reason": "end_turn"}


class _BuggyMathTools(ToolRegistry):
    """Multiplication is off by one — the kind of subtle bug that Volo should catch."""

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        if tool == "add":
            return {"result": int(request["a"]) + int(request["b"])}
        if tool == "multiply":
            # BUG (deliberate): off-by-one in the product.
            return {"result": int(request["a"]) * int(request["b"]) + 1}
        raise KeyError(f"unknown tool: {tool!r}")


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    a = int(payload.get("a", 0))
    b = int(payload.get("b", 0))
    c = int(payload.get("c", 1))

    model = ModelProviderProxy(
        _DeterministicModel(),
        provider_name="echo",
        model_name="echo-1",
    )
    tools = ToolRegistryProxy(_BuggyMathTools())

    rec = get_active_recorder()
    if rec is not None:
        rec.record_step(DecisionPayload(label="plan_compute", chosen=f"({a}+{b})*{c}"))

    model.complete({"prompt": f"plan: compute ({a}+{b})*{c}"})
    sum_ = tools.call("add", {"a": a, "b": b})["result"]
    prod = tools.call("multiply", {"a": sum_, "b": c})["result"]
    model.complete({"prompt": f"summary: answer is {prod}"})

    return {"answer": prod}
