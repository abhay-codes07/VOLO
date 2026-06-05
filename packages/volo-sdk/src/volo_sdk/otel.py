"""OpenTelemetry trace importer (ADR-0009, bible §4 subsystem 1, M7).

Reads an OTel JSONL trace file and emits a Volo ``Recording``. The mapping:

* Spans whose name starts with ``llm.`` / ``gen_ai.`` or whose attributes carry a
  ``gen_ai.system`` field → ``ModelCallPayload``.
* Spans whose name starts with ``tool.`` / ``function.`` or whose attributes carry a
  ``tool.name`` / ``function.name`` field → ``ToolCallPayload``.
* Spans carrying a ``volo.decision.label`` attribute → ``DecisionPayload``.
* Span parent (``parent_id``) is preserved on the ``Step``.
* Resource attributes go into ``RunMeta.extra``.

We accept three on-disk shapes:

1. JSONL — one OTel span object per line.
2. OTLP JSON — a top-level ``{"resourceSpans": [...]}`` object (the OTel collector export
   format). Spans are extracted from ``resourceSpans[*].scopeSpans[*].spans``.
3. A bare JSON array of span objects.

The importer is **pure** — it never calls a live model or tool. The ``Recording`` it
produces is fully equivalent to one captured via the SDK proxies; the runner can drive a
Tier-2 replay against it directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from volo_core import (
    DecisionPayload,
    ModelCallPayload,
    Recording,
    RunMeta,
    Step,
    ToolCallPayload,
)
from volo_core.recording import StepPayload


def import_otel_trace(
    path: str | Path,
    *,
    agent_name: str | None = None,
    framework: str = "otel",
) -> Recording:
    """Import an OTel trace file (JSONL / OTLP JSON / array JSON) into a Volo Recording."""
    spans, resource_attrs = _load_spans(Path(path))
    if not spans:
        return Recording(
            agent_meta=RunMeta(framework=framework, agent_name=agent_name, extra=resource_attrs),
        )

    # OTel spans don't have a guaranteed insertion order; sort by start time so trajectories
    # are reproducible.
    spans = sorted(spans, key=lambda s: _start_ns(s))

    # Build a (span_id → Step.step_id) map so we can wire parent_id correctly.
    by_span_id: dict[str, Step] = {}

    rec = Recording(
        agent_meta=RunMeta(framework=framework, agent_name=agent_name, extra=resource_attrs),
    )
    for span in spans:
        payload = _classify(span)
        if payload is None:
            continue
        parent_span = _span_id(span, key="parentSpanId") or _span_id(span, key="parent_id")
        parent_step_id = by_span_id[parent_span].step_id if parent_span in by_span_id else None
        step = rec.add_step(payload, parent_id=parent_step_id)
        step.latency_ms = _latency_ms(span)
        attrs = _attrs(span)
        if isinstance(attrs.get("gen_ai.usage.total_tokens"), int):
            step.tokens = attrs["gen_ai.usage.total_tokens"]
        if isinstance(attrs.get("gen_ai.cost_usd"), (int, float)):
            step.cost_usd = float(attrs["gen_ai.cost_usd"])
        own_id = _span_id(span, key="spanId") or _span_id(span, key="span_id")
        if own_id:
            by_span_id[own_id] = step
    return rec


# ── loaders ──────────────────────────────────────────────────────────────────


def _load_spans(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return ``(spans, resource_attrs)``."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return [], {}

    # Try OTLP JSON: { "resourceSpans": [ { "resource": {...}, "scopeSpans": [...] } ] }
    if text.startswith("{"):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, dict) and "resourceSpans" in doc:
            return _flatten_otlp(doc), _extract_resource_attrs(doc)
        # Bare object — wrap as a single-span list.
        if isinstance(doc, dict):
            return [doc], {}

    # Try JSON array.
    if text.startswith("["):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, list):
            return [s for s in doc if isinstance(s, dict)], {}

    # Fall back to JSONL.
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            span = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(span, dict):
            out.append(span)
    return out, {}


def _flatten_otlp(doc: dict[str, Any]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for rs in doc.get("resourceSpans", []) or []:
        if not isinstance(rs, dict):
            continue
        for ss in rs.get("scopeSpans", []) or []:
            if not isinstance(ss, dict):
                continue
            for span in ss.get("spans", []) or []:
                if isinstance(span, dict):
                    spans.append(span)
    return spans


def _extract_resource_attrs(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rs in doc.get("resourceSpans", []) or []:
        resource = (rs or {}).get("resource") if isinstance(rs, dict) else None
        for kv in (resource or {}).get("attributes", []) or []:
            k = kv.get("key") if isinstance(kv, dict) else None
            v = _otlp_value(kv.get("value")) if isinstance(kv, dict) else None
            if k is not None:
                out[k] = v
    return out


# ── classification ───────────────────────────────────────────────────────────


def _classify(span: dict[str, Any]) -> StepPayload | None:
    """Pick the appropriate Volo payload type for an OTel span."""
    attrs = _attrs(span)
    name = str(span.get("name") or "").lower()

    # Decision (custom Volo attribute)
    if "volo.decision.label" in attrs:
        return DecisionPayload(
            label=str(attrs["volo.decision.label"]),
            chosen=_str_or_none(attrs.get("volo.decision.chosen")),
            rationale=_str_or_none(attrs.get("volo.decision.rationale")),
        )

    # Model call
    if (
        name.startswith("llm.")
        or name.startswith("gen_ai.")
        or "gen_ai.system" in attrs
        or "llm.model_name" in attrs
    ):
        provider = attrs.get("gen_ai.system") or attrs.get("llm.provider") or "unknown"
        model = attrs.get("gen_ai.request.model") or attrs.get("llm.model_name") or "unknown"
        request = _decode_or_empty(attrs.get("gen_ai.request") or attrs.get("llm.input"))
        response = _decode_or_empty(attrs.get("gen_ai.response") or attrs.get("llm.output"))
        return ModelCallPayload(
            provider=str(provider),
            model=str(model),
            request=request,
            response=response or None,
        )

    # Tool call
    if (
        name.startswith("tool.")
        or name.startswith("function.")
        or "tool.name" in attrs
        or "function.name" in attrs
    ):
        tool = attrs.get("tool.name") or attrs.get("function.name") or _trim_prefix(name)
        request = _decode_or_empty(attrs.get("tool.input") or attrs.get("function.input"))
        response = _decode_or_empty(attrs.get("tool.output") or attrs.get("function.output"))
        return ToolCallPayload(
            tool=str(tool),
            request=request,
            response=response or None,
        )

    return None


# ── helpers ──────────────────────────────────────────────────────────────────


def _attrs(span: dict[str, Any]) -> dict[str, Any]:
    """Return a flat attribute dict for either JSONL-style or OTLP-style spans."""
    raw = span.get("attributes")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        out: dict[str, Any] = {}
        for kv in raw:
            if isinstance(kv, dict) and "key" in kv:
                out[str(kv["key"])] = _otlp_value(kv.get("value"))
        return out
    return {}


def _otlp_value(v: Any) -> Any:
    """Unwrap an OTLP ``AnyValue`` envelope."""
    if not isinstance(v, dict):
        return v
    for key in ("stringValue", "intValue", "boolValue", "doubleValue"):
        if key in v:
            val = v[key]
            if key == "intValue" and isinstance(val, str):
                try:
                    return int(val)
                except ValueError:
                    return val
            return val
    if "kvlistValue" in v:
        return {
            kv["key"]: _otlp_value(kv.get("value"))
            for kv in (v["kvlistValue"].get("values") or [])
            if isinstance(kv, dict) and "key" in kv
        }
    if "arrayValue" in v:
        return [_otlp_value(x) for x in (v["arrayValue"].get("values") or [])]
    return v


def _decode_or_empty(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            doc = json.loads(raw)
            return doc if isinstance(doc, dict) else {"text": raw}
        except json.JSONDecodeError:
            return {"text": raw}
    return {}


def _start_ns(span: dict[str, Any]) -> int:
    for k in ("startTimeUnixNano", "start_time_unix_nano", "startTime", "start"):
        if k in span:
            try:
                return int(span[k])
            except (TypeError, ValueError):
                continue
    return 0


def _end_ns(span: dict[str, Any]) -> int:
    for k in ("endTimeUnixNano", "end_time_unix_nano", "endTime", "end"):
        if k in span:
            try:
                return int(span[k])
            except (TypeError, ValueError):
                continue
    return 0


def _latency_ms(span: dict[str, Any]) -> float | None:
    start = _start_ns(span)
    end = _end_ns(span)
    if start and end and end >= start:
        return (end - start) / 1_000_000.0
    return None


def _span_id(span: dict[str, Any], *, key: str) -> str | None:
    v = span.get(key)
    return str(v) if v is not None and str(v) else None


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


def _trim_prefix(name: str) -> str:
    for prefix in ("tool.", "function.", "llm.", "gen_ai."):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


__all__ = ["import_otel_trace"]
