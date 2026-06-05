"""volo-sdk — the Capture SDK (bible §4, subsystem 1).

Public surface:

* ``Recorder`` — manual API; the recommended low-level primitive.
* ``record`` — a context manager wrapping ``Recorder`` for "open / close" ergonomics.
* ``RecorderConfig`` — toggles for redaction, output dir, schema-version pinning.
* ``import_otel_trace`` — build a ``Recording`` from an OTel trace (JSONL / OTLP-JSON /
  bare-array). Implemented in M7; framework adapters live under ``integrations/``.
"""

from volo_sdk.otel import import_otel_trace
from volo_sdk.proxies import ModelProviderProxy, ToolRegistryProxy
from volo_sdk.recorder import (
    Recorder,
    RecorderConfig,
    record,
)

__all__ = [
    "ModelProviderProxy",
    "Recorder",
    "RecorderConfig",
    "ToolRegistryProxy",
    "import_otel_trace",
    "record",
]
