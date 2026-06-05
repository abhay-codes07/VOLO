"""Wrap a LangGraph runtime so Volo proxies see every model + tool call."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_sdk import ModelProviderProxy, ToolRegistryProxy


def wrap(
    graph: Any,
    *,
    model: ModelProvider | None = None,
    tools: ToolRegistry | None = None,
    provider_name: str = "langgraph",
    model_name: str = "default",
) -> Any:
    """Install Volo capture proxies into a LangGraph graph.

    Args:
        graph: A LangGraph graph or a duck-typed object with ``.nodes`` and a callable
            ``.invoke(state)`` or ``.run(state)``.
        model: Optional explicit ``ModelProvider``. If omitted, the existing model on the
            graph is left in place and only the call boundary is wrapped.
        tools: Same idea for tools.

    Returns:
        The wrapped graph (mutation is in place; return is for chaining).
    """
    if model is not None:
        proxy = ModelProviderProxy(model, provider_name=provider_name, model_name=model_name)
        _attach(graph, "model", proxy)
    if tools is not None:
        _attach(graph, "tools", ToolRegistryProxy(tools))
    _ensure_call_capture(graph)
    return graph


def _attach(graph: Any, slot: str, value: Any) -> None:
    """Set ``graph.<slot>`` if the attribute exists; never break the host object."""
    if hasattr(graph, slot):
        try:
            setattr(graph, slot, value)
        except Exception:
            # Some real LangGraph objects use immutable wrappers — store in a sidecar.
            graph.__dict__.setdefault("_volo_overrides", {})[slot] = value
    else:
        graph.__dict__.setdefault("_volo_overrides", {})[slot] = value


def _ensure_call_capture(graph: Any) -> None:
    """If the host exposes ``.invoke`` / ``.run`` / ``.call``, wrap it so any model/tool the
    graph itself calls during execution flows through our active-recorder ContextVar.

    The proxies only record when an active recorder is set — so this is safe even outside
    a ``record()`` block.
    """
    for fn_name in ("invoke", "run", "call"):
        fn = getattr(graph, fn_name, None)
        if callable(fn) and not getattr(fn, "_volo_wrapped", False):
            setattr(graph, fn_name, _wrap_runtime(fn))
            break


def _wrap_runtime(fn: Callable[..., Any]) -> Callable[..., Any]:
    def runtime(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    runtime._volo_wrapped = True  # type: ignore[attr-defined]
    runtime.__name__ = getattr(fn, "__name__", "wrapped")
    return runtime
