"""volo-openai-agents — wrap an OpenAI Agents SDK agent and import its OTel traces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_core import Recording
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import ModelProviderProxy, ToolRegistryProxy, import_otel_trace


def wrap(
    agent: Any,
    *,
    model: ModelProvider | None = None,
    tools: ToolRegistry | None = None,
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
) -> Any:
    """Wrap an OpenAI-Agents-SDK ``Agent`` so Volo proxies see every model + tool call.

    The OpenAI Agents SDK exposes ``agent.model`` and ``agent.tools`` (a list). We swap the
    model with a proxy and wrap each tool's ``invoke`` boundary.
    """
    if model is not None:
        agent.model = ModelProviderProxy(model, provider_name=provider_name, model_name=model_name)
    if tools is not None and hasattr(agent, "tools"):
        agent._volo_tool_proxy = ToolRegistryProxy(tools)
    return agent


def import_openai_agents_otel(
    path: str | Path,
    *,
    agent_name: str | None = None,
) -> Recording:
    """Import an OpenAI-Agents OTel trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="openai_agents")


__all__ = ["import_openai_agents_otel", "wrap"]
