"""volo-pydantic-ai — wrap a Pydantic AI ``Agent`` and import its OTel traces.

A Pydantic AI ``Agent`` carries a ``model`` and runs via ``run_sync`` / ``run``; tools are
registered functions. Duck-typed like the M7 integrations: swap ``agent.model`` with a
``ModelProviderProxy``, expose a tool proxy, and decorate the run entrypoint with a ``decision``
step.
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
    provider_name: str = "pydantic_ai",
    model_name: str = "default",
) -> Any:
    """Wrap a Pydantic AI ``Agent`` so Volo proxies see every model + tool call."""
    if model is not None and hasattr(agent, "model"):
        agent.model = ModelProviderProxy(model, provider_name=provider_name, model_name=model_name)
    if tools is not None:
        agent._volo_tool_proxy = ToolRegistryProxy(tools)
    _decorate_run(agent, ("run_sync", "run"), "pydantic_ai_run")
    return agent


def _decorate_run(obj: Any, names: tuple[str, ...], label: str) -> None:
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


def import_pydantic_ai_otel(path: str | Path, *, agent_name: str | None = None) -> Recording:
    """Import a Pydantic AI OTel trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="pydantic_ai")


__all__ = ["import_pydantic_ai_otel", "wrap"]
