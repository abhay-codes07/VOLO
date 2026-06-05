"""A trivial echo "agent" — takes ``{"text": str}`` and returns ``{"echo": str}``.

Exercises the full capture path with no LLM calls:

1. Wraps a deterministic in-process "model" in a ``ModelProviderProxy`` so each invocation
   shows up as a ``model_call`` step on the active Recorder.
2. Wraps a tiny in-process tool registry in a ``ToolRegistryProxy`` so tool invocations show up
   as ``tool_call`` steps too.

This is the e2e dogfood target used by the test suite and the README quickstart.
"""

from __future__ import annotations

from typing import Any

from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import ModelProviderProxy, ToolRegistryProxy


class _EchoModel(ModelProvider):
    """Returns the user's text verbatim — deterministic, zero-cost."""

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        text = str(request.get("prompt", ""))
        return {"text": text, "stop_reason": "end_turn"}


class _EchoTools(ToolRegistry):
    """A single ``upper`` tool that uppercases its input. Deterministic, zero-cost."""

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        if tool != "upper":
            raise KeyError(f"unknown tool: {tool!r}")
        return {"result": str(request.get("text", "")).upper()}


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """The agent entrypoint.

    Steps it takes:
    1. Call ``upper`` tool on the input.
    2. Ask the (fake) model to "echo" the uppercased text.
    3. Return ``{"echo": ...}``.

    All three calls go through proxies, so a wrapping Recorder sees three steps.
    """
    text = "" if payload is None else str(payload.get("text", ""))

    tools = ToolRegistryProxy(_EchoTools())
    model = ModelProviderProxy(_EchoModel(), provider_name="echo", model_name="echo-1")

    upper = tools.call("upper", {"text": text})["result"]
    completion = model.complete({"prompt": upper})
    return {"echo": completion["text"]}
