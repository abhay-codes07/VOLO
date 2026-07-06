"""volo-semantic-kernel — wrap a Semantic Kernel ``Kernel`` and import its OTel traces.

A Semantic Kernel ``Kernel`` holds AI services in ``.services`` (service_id → client) and plugins
in ``.plugins``; completions run via ``invoke`` / ``invoke_prompt``. Duck-typed like the M7
integrations: replace each service with a ``ModelProviderProxy``, expose a tool proxy, and
decorate the invoke entrypoint with a ``decision`` step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_core import Recording, get_active_recorder
from volo_core.interfaces import ModelProvider, ToolRegistry
from volo_core.recording import DecisionPayload
from volo_sdk import ModelProviderProxy, ToolRegistryProxy, import_otel_trace


def wrap(
    kernel: Any,
    *,
    model: ModelProvider | None = None,
    tools: ToolRegistry | None = None,
    provider_name: str = "semantic_kernel",
    model_name: str = "default",
) -> Any:
    """Wrap a Semantic Kernel ``Kernel`` so Volo proxies see every model + tool call."""
    if model is not None and isinstance(getattr(kernel, "services", None), dict):
        proxy = ModelProviderProxy(model, provider_name=provider_name, model_name=model_name)
        for service_id in list(kernel.services):
            kernel.services[service_id] = proxy
    if tools is not None and hasattr(kernel, "plugins"):
        kernel._volo_tool_proxy = ToolRegistryProxy(tools)
    _decorate_run(kernel, ("invoke", "invoke_prompt", "run"), "kernel_invoke")
    return kernel


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


def import_semantic_kernel_otel(path: str | Path, *, agent_name: str | None = None) -> Recording:
    """Import a Semantic Kernel OTel trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="semantic_kernel")


__all__ = ["import_semantic_kernel_otel", "wrap"]
