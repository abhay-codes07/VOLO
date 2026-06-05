"""Lock the OTel importer's public surface — signature must stay stable for adapters."""

from __future__ import annotations

import inspect

from volo_sdk import import_otel_trace


def test_otel_importer_signature_is_stable() -> None:
    sig = inspect.signature(import_otel_trace)
    assert set(sig.parameters.keys()) == {"path", "agent_name", "framework"}
    assert sig.parameters["framework"].default == "otel"


def test_otel_importer_is_no_longer_a_stub() -> None:
    """The M7 seam is now implemented — no NotImplementedError in source."""
    src = inspect.getsource(import_otel_trace) or ""
    assert "NotImplementedError" not in src
