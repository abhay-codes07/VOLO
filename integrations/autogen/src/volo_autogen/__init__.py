"""volo-autogen — wrap an AutoGen agent/team and import its OTel traces.

AutoGen v0.4 (`autogen-agentchat`) agents carry a ``model_client``; the legacy 0.2 line used
``llm``. Both are duck-typed here, matching the M7 integrations: swap the model attribute with a
``ModelProviderProxy``, wrap tools, and decorate the run entrypoint so the trajectory records a
``decision`` step per run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_core import Recording, get_active_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_core.recording import DecisionPayload
from volo_sdk import ModelProviderProxy, ToolRegistryProxy, import_otel_trace


def wrap(
    agent: Any,
    *,
    model: ModelProvider | None = None,
    tools: ToolRegistry | None = None,
    provider_name: str = "autogen",
    model_name: str = "default",
) -> Any:
    """Wrap an AutoGen agent so Volo proxies see every model + tool call."""
    if model is not None:
        proxy = ModelProviderProxy(model, provider_name=provider_name, model_name=model_name)
        if hasattr(agent, "model_client"):
            agent.model_client = proxy
        elif hasattr(agent, "llm"):
            agent.llm = proxy
    if tools is not None and hasattr(agent, "tools"):
        agent.tools = ToolRegistryProxy(tools)
    _decorate_run(agent, ("run", "run_stream", "generate_reply"), "autogen_run")
    return agent


def _decorate_run(obj: Any, names: tuple[str, ...], label: str) -> None:
    """Decorate the first present entrypoint to emit a ``decision`` step, then delegate."""
    for name in names:
        fn = getattr(obj, name, None)
        if callable(fn) and not getattr(fn, "_volo_wrapped", False):

            def wrapped(*args: Any, __orig: Any = fn, __label: str = label, **kwargs: Any) -> Any:
                rec = get_active_recorder()
                if rec is not None:
                    rec.record_step(
                        DecisionPayload(label=__label, chosen=getattr(__orig, "__name__", "run"))
                    )
                return __orig(*args, **kwargs)

            wrapped._volo_wrapped = True  # type: ignore[attr-defined]
            wrapped.__name__ = getattr(fn, "__name__", name)
            setattr(obj, name, wrapped)
            return


def import_autogen_otel(path: str | Path, *, agent_name: str | None = None) -> Recording:
    """Import an AutoGen OTel trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="autogen")


__all__ = ["import_autogen_otel", "wrap"]
