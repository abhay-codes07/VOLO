"""Tier-2 simulator — hybrid synthesis with flag-on-unknown sentinel (ADR-0009).

Two paths today:

* **(a) Constrained local-model generation** via Ollama. Given a tool's ``output_schema``,
  the local model produces a JSON object that validates against the schema. **Shipped.**
* **(c) Flag-on-unknown sentinel.** If (a) cannot produce a validated response (no schema, no
  Ollama, validation failure), the synthesizer returns ``None``; ``Tier2Replayer`` raises
  ``Tier2Miss`` so the runner can mark the step as ``synthesis = "flagged"``.

The (b) source-/spec-informed path is reserved as the next implementation slot — the
``SourceInformedSynthesizer`` stub lands in this module so the resolution order can be wired
end-to-end before that work begins.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from volo_core import Recording, ToolSpec, cache_key
from volo_core.interfaces import ModelProvider, SimulatedEnvironment, ToolRegistry
from volo_simulator.replayer import ReplayMiss, Tier1Replayer

# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────


class Tier2Miss(LookupError):
    """Raised when Tier-2 cannot synthesize a faithful response.

    The runner records the offending step with ``synthesis = "flagged"`` and continues; the
    reliability engine treats flagged steps as "unknown — not the agent's fault".
    """


class Synthesizer(Protocol):
    """A strategy that may produce a tool / model response for an un-recorded input.

    Implementations return ``None`` to abstain so the next strategy can attempt.
    """

    def synthesize_tool(
        self,
        tool: str,
        request: dict[str, Any],
        spec: ToolSpec | None,
        *,
        seed: int,
    ) -> dict[str, Any] | None: ...

    def synthesize_model(
        self,
        provider: str,
        model: str,
        request: dict[str, Any],
        *,
        seed: int,
    ) -> dict[str, Any] | None: ...


# ──────────────────────────────────────────────────────────────────────────────
# (a) Ollama constrained-generation synthesizer
# ──────────────────────────────────────────────────────────────────────────────


class OllamaConstrainedSynthesizer:
    """Ollama-backed JSON-constrained synthesizer.

    Defers the actual HTTP call to a ``ModelProvider`` injected at construction time so we
    can test without a running daemon. The default factory uses
    ``volo_models.OllamaProvider``.
    """

    def __init__(
        self,
        *,
        provider: ModelProvider | None = None,
        timeout_s: float = 8.0,
        max_attempts: int = 2,
    ) -> None:
        self._provider = provider
        self.timeout_s = timeout_s
        self.max_attempts = max_attempts
        self._stats: Counter[str] = Counter()

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def _get_provider(self) -> ModelProvider | None:
        if self._provider is not None:
            return self._provider
        try:
            from volo_models import OllamaProvider  # local import — Ollama is optional
        except ImportError:  # pragma: no cover
            return None
        try:
            self._provider = OllamaProvider()
            return self._provider
        except Exception:  # pragma: no cover — daemon optional
            return None

    def synthesize_tool(
        self,
        tool: str,
        request: dict[str, Any],
        spec: ToolSpec | None,
        *,
        seed: int,
    ) -> dict[str, Any] | None:
        if spec is None or spec.output_schema is None:
            self._stats["miss_no_schema"] += 1
            return None
        prov = self._get_provider()
        if prov is None:
            self._stats["miss_no_ollama"] += 1
            return None

        prompt = _build_tool_prompt(tool, request, spec, seed=seed)
        for attempt in range(self.max_attempts):
            try:
                raw = prov.complete(
                    {
                        "prompt": prompt,
                        "format": "json",
                        "seed": seed + attempt,
                        "temperature": 0.0,
                    }
                )
            except Exception:
                self._stats["miss_provider_error"] += 1
                return None
            payload = _extract_json(raw)
            if payload is None:
                continue
            if _validates(payload, spec.output_schema):
                self._stats["hit"] += 1
                return payload
        self._stats["miss_invalid_json"] += 1
        return None

    def synthesize_model(
        self,
        provider: str,
        model: str,
        request: dict[str, Any],
        *,
        seed: int,
    ) -> dict[str, Any] | None:
        # Model-call synthesis is intentionally a stub at Tier-2 (a) — recorded model calls
        # are the high-fidelity case; un-recorded model calls usually mean the agent diverged
        # earlier, which is itself a signal to flag.
        self._stats["model_call_flagged"] += 1
        return None


def _build_tool_prompt(
    tool: str,
    request: dict[str, Any],
    spec: ToolSpec,
    *,
    seed: int,
) -> str:
    """Compose a constrained prompt for the local model."""
    schema = json.dumps(spec.output_schema, indent=2, sort_keys=True)
    req = json.dumps(request, indent=2, sort_keys=True)
    desc = spec.description or "(no description)"
    return (
        "You are simulating the response of a tool inside a deterministic test harness.\n"
        "Return ONLY a single JSON object that VALIDATES against the schema below.\n"
        "Do not add prose, code fences, or explanation.\n\n"
        f"TOOL: {tool}\n"
        f"DESCRIPTION: {desc}\n\n"
        f"REQUEST:\n{req}\n\n"
        f"OUTPUT_SCHEMA:\n{schema}\n\n"
        f"# seed={seed} — your response must be deterministic given this seed.\n"
    )


# ──────────────────────────────────────────────────────────────────────────────
# (b) Source-/spec-informed synthesizer — ADR-0009, ADR-0010
# ──────────────────────────────────────────────────────────────────────────────


_HINT_PYTHON = "python"
_HINT_OPENAPI = "openapi"
_HINT_FIXTURE = "fixture"


def _parse_hint(hint: str) -> tuple[str, str] | None:
    """Return ``(kind, body)`` for a ``ToolSpec.source_hint``.

    Supported forms (case-insensitive prefix):

    * ``python:module.path:attr`` — a callable shadow.
    * ``openapi:URL`` — an OpenAPI 3.x spec.
    * ``fixture:PATH`` — a JSON file mapping canonical-request hash → response.

    Returns ``None`` if the hint can't be parsed.
    """
    if not hint or ":" not in hint:
        return None
    prefix, _, body = hint.partition(":")
    prefix = prefix.lower().strip()
    body = body.strip()
    if prefix in (_HINT_PYTHON, _HINT_OPENAPI, _HINT_FIXTURE) and body:
        return prefix, body
    return None


class SourceInformedSynthesizer:
    """Tier-2 (b): use a tool's declared shadow / spec to synthesize a faithful response.

    Three resolution paths, dispatched by ``ToolSpec.source_hint``:

    * ``python:module.path:attr`` — import and call. The attr must be a callable taking a
      ``request: dict[str, Any]`` and returning a dict that validates against
      ``output_schema``. **Highest fidelity.**
    * ``openapi:URL`` — parse the OpenAPI document, find a matching operation, derive a
      minimal example response from its response schema. Best-effort, no live HTTP.
    * ``fixture:PATH`` — load a JSON file ``{cache_key: response}``. Indexed by the
      canonical hash of the request.

    Validates every synthesized response against ``output_schema`` before returning. On any
    failure path (malformed hint, import error, validation miss) returns ``None`` so the
    Tier-2 chain falls through to constrained generation or to the ``Tier2Miss`` sentinel.

    Never raises across the public surface — strategies abstain by returning ``None``.

    **Security (ADR-0012).** A ``source_hint`` is attacker-controlled when a Recording comes
    from an untrusted source (shared/downloaded). The ``python:`` resolver *imports and calls*
    code, and ``fixture:`` / ``openapi:`` *read files* — so both are gated:

    * ``trust_source_hints=False`` (default) — ``python:`` is **never** executed; file hints
      are only honoured if confined to ``base_dir`` (and refused entirely when ``base_dir`` is
      ``None``). Safe to point at an untrusted recording.
    * ``trust_source_hints=True`` — full behaviour, for recordings you authored locally.
    """

    def __init__(
        self,
        *,
        trust_source_hints: bool = False,
        base_dir: Path | None = None,
    ) -> None:
        self._trust = trust_source_hints
        self._base_dir = base_dir
        self._openapi_cache: dict[str, dict[str, Any]] = {}
        self._fixture_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._stats: Counter[str] = Counter()

    def _resolve_file_hint(self, raw: str) -> Path | None:
        """Resolve a ``fixture:`` / ``openapi:`` path under the trust policy, or ``None``.

        Trusted: any path (local dev). Untrusted: relative paths confined to ``base_dir``;
        absolute paths and any escape via ``..``/symlink are refused.
        """
        body = raw[len("file://") :] if raw.startswith("file://") else raw
        path = Path(body)
        if self._trust:
            return path
        if self._base_dir is None:
            return None
        if path.is_absolute():
            return None
        base = self._base_dir.resolve()
        resolved = (base / path).resolve()
        if base != resolved and base not in resolved.parents:
            return None
        return resolved

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def synthesize_tool(
        self,
        tool: str,
        request: dict[str, Any],
        spec: ToolSpec | None,
        *,
        seed: int,
    ) -> dict[str, Any] | None:
        if spec is None or not spec.source_hint:
            self._stats["miss_no_hint"] += 1
            return None
        parsed = _parse_hint(spec.source_hint)
        if parsed is None:
            self._stats["miss_malformed_hint"] += 1
            return None
        kind, body = parsed
        if kind == _HINT_PYTHON and not self._trust:
            # Refuse to import+call code named by an untrusted hint (ADR-0012).
            self._stats["miss_python_untrusted"] += 1
            return None
        try:
            if kind == _HINT_PYTHON:
                out = self._call_python_shadow(body, request)
            elif kind == _HINT_OPENAPI:
                out = self._derive_from_openapi(body, tool, request, spec)
            else:  # _HINT_FIXTURE
                out = self._lookup_fixture(body, request)
        except Exception:
            self._stats[f"miss_{kind}_error"] += 1
            return None
        if out is None:
            self._stats[f"miss_{kind}_no_match"] += 1
            return None
        if spec.output_schema is not None and not _validates(out, spec.output_schema):
            self._stats[f"miss_{kind}_invalid"] += 1
            return None
        self._stats[f"hit_{kind}"] += 1
        return out

    def synthesize_model(
        self,
        provider: str,
        model: str,
        request: dict[str, Any],
        *,
        seed: int,
    ) -> dict[str, Any] | None:
        # Same rationale as ADR-0009: model-call synthesis is reserved for future work.
        # Source-informed paths typically describe tools, not models.
        self._stats["model_call_flagged"] += 1
        return None

    # ── (b1) python shadow ───────────────────────────────────────────────────

    def _call_python_shadow(
        self,
        body: str,
        request: dict[str, Any],
    ) -> dict[str, Any] | None:
        """``body`` is ``module.dotted.path:attr``."""
        import importlib

        if ":" not in body:
            return None
        mod_path, attr = body.split(":", 1)
        mod = importlib.import_module(mod_path)
        target: Any = mod
        for piece in attr.split("."):
            target = getattr(target, piece)
        if not callable(target):
            return None
        out = target(dict(request))
        return out if isinstance(out, dict) else None

    # ── (b2) openapi ─────────────────────────────────────────────────────────

    def _derive_from_openapi(
        self,
        url: str,
        tool: str,
        request: dict[str, Any],
        spec: ToolSpec,
    ) -> dict[str, Any] | None:
        """Best-effort response derivation from an OpenAPI spec.

        Today we only support ``file://`` and bare paths — no live HTTP — so the test
        harness can drop a spec on disk and we can derive an example without touching the
        network. Live HTTP can be added when M7 framework integrations ship.
        """
        spec_doc = self._openapi_cache.get(url)
        if spec_doc is None:
            fp = self._resolve_file_hint(url)
            if fp is None:
                return None
            spec_doc = _load_openapi(fp)
            if spec_doc is None:
                return None
            self._openapi_cache[url] = spec_doc

        operation = _find_openapi_operation(spec_doc, tool)
        if operation is None:
            return None
        response_schema = _extract_openapi_response_schema(operation)
        if response_schema is None:
            return None
        # Prefer the tool's declared output_schema for shape; fall back to the OpenAPI
        # schema for examples.
        target_schema = spec.output_schema or response_schema
        example = _example_for_schema(response_schema)
        if example is None or not _validates(example, target_schema):
            return None
        return cast(dict[str, Any], example)

    # ── (b3) fixture ─────────────────────────────────────────────────────────

    def _lookup_fixture(
        self,
        path: str,
        request: dict[str, Any],
    ) -> dict[str, Any] | None:
        fixture = self._fixture_cache.get(path)
        if fixture is None:
            fp = self._resolve_file_hint(path)
            if fp is None or not fp.exists():
                return None
            raw = json.loads(fp.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            fixture = {str(k): v for k, v in raw.items() if isinstance(v, dict)}
            self._fixture_cache[path] = fixture
        key = cache_key("fixture", request)
        hit = fixture.get(key)
        if hit is None:
            return None
        return dict(hit)


# ── OpenAPI helpers (tiny, no dependencies) ──────────────────────────────────


def _load_openapi(path: Path) -> dict[str, Any] | None:
    """Load an OpenAPI doc from an already-trust-resolved path (see ``_resolve_file_hint``)."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # YAML support is a follow-up — keep zero-dep for now.
        return None
    return parsed if isinstance(parsed, dict) else None


def _find_openapi_operation(spec: dict[str, Any], tool: str) -> dict[str, Any] | None:
    """Match a tool name to an OpenAPI operation by ``operationId`` or path tail."""
    paths = spec.get("paths") or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            if op.get("operationId") == tool:
                return op
            if path.rstrip("/").endswith(f"/{tool}") and method.lower() in {"get", "post"}:
                return op
    return None


def _extract_openapi_response_schema(op: dict[str, Any]) -> dict[str, Any] | None:
    responses = op.get("responses") or {}
    for status_code in ("200", "201", "default"):
        node = responses.get(status_code)
        if not isinstance(node, dict):
            continue
        content = node.get("content") or {}
        if not isinstance(content, dict):
            continue
        for _media, media_node in content.items():
            if isinstance(media_node, dict) and isinstance(media_node.get("schema"), dict):
                return cast(dict[str, Any], media_node["schema"])
    return None


def _example_for_schema(schema: dict[str, Any]) -> Any:
    """Derive a minimal example value from a JSON Schema fragment."""
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    t = schema.get("type")
    if t == "object":
        out: dict[str, Any] = {}
        props = schema.get("properties") or {}
        for k, sub in props.items():
            example = _example_for_schema(sub) if isinstance(sub, dict) else None
            if example is not None:
                out[k] = example
        # Ensure required keys are present.
        for req in schema.get("required") or []:
            if req not in out:
                sub = props.get(req)
                fallback = _example_for_schema(sub) if isinstance(sub, dict) else ""
                out[req] = fallback if fallback is not None else ""
        return out
    if t == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            sample = _example_for_schema(items)
            return [sample] if sample is not None else []
        return []
    if t == "string":
        return ""
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    return None


# ──────────────────────────────────────────────────────────────────────────────
# JSON helpers
# ──────────────────────────────────────────────────────────────────────────────


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(response: dict[str, Any]) -> dict[str, Any] | None:
    """Pull a JSON object out of an Ollama-style ``{text: str, ...}`` response."""
    text = response.get("text") or response.get("response") or ""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    # Try strict parse first.
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if m is None:
            return None
        try:
            out = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return out if isinstance(out, dict) else None


def _validates(value: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Minimal JSON-Schema check — type + required, no fancy keywords.

    We don't depend on ``jsonschema`` to keep Tier-2 zero-cost at install. The runtime check
    is deliberately strict in the dimensions that matter (shape) and permissive elsewhere.
    """
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            return False
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                return False
        props = schema.get("properties") or {}
        for key, sub_schema in props.items():
            if key in value and not _validates_any(value[key], sub_schema):
                return False
        return True
    return _validates_any(value, schema)


def _validates_any(value: Any, schema: dict[str, Any]) -> bool:
    t = schema.get("type")
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "array":
        if not isinstance(value, list):
            return False
        items = schema.get("items")
        if items is None:
            return True
        return all(_validates_any(v, items) for v in value)
    if t == "object":
        return isinstance(value, dict) and _validates(value, schema)
    return True  # unknown / unconstrained → permit


# ──────────────────────────────────────────────────────────────────────────────
# Tier-2 chained replayer
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class Tier2Stats:
    cache_hits: int = 0
    synthesized: int = 0
    flagged: int = 0


class _ChainedToolRegistry(ToolRegistry):
    def __init__(
        self,
        tier1: ToolRegistry,
        synthesizers: list[Synthesizer],
        tool_specs: dict[str, ToolSpec],
        seed: int,
        stats: Tier2Stats,
    ) -> None:
        self._tier1 = tier1
        self._synths = synthesizers
        self._specs = tool_specs
        self._seed = seed
        self._stats = stats

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        try:
            out = self._tier1.call(tool, request)
            self._stats.cache_hits += 1
            return out
        except ReplayMiss:
            spec = self._specs.get(tool)
            key_seed = int(cache_key("tier2_tool", tool, request)[:8], 16) ^ self._seed
            for synth in self._synths:
                synthesized = synth.synthesize_tool(tool, request, spec, seed=key_seed)
                if synthesized is not None:
                    self._stats.synthesized += 1
                    return synthesized
            self._stats.flagged += 1
            raise Tier2Miss(
                f"tool={tool!r} input not recorded and no synthesizer accepted it "
                f"(spec={'yes' if spec else 'no'})",
            ) from None


class _ChainedModelProvider(ModelProvider):
    def __init__(
        self,
        tier1: ModelProvider,
        synthesizers: list[Synthesizer],
        provider: str,
        model: str,
        seed: int,
        stats: Tier2Stats,
    ) -> None:
        self._tier1 = tier1
        self._synths = synthesizers
        self._provider = provider
        self._model = model
        self._seed = seed
        self._stats = stats

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            out = self._tier1.complete(request)
            self._stats.cache_hits += 1
            return out
        except ReplayMiss:
            key_seed = (
                int(cache_key("tier2_model", self._provider, self._model, request)[:8], 16)
                ^ self._seed
            )
            for synth in self._synths:
                synthesized = synth.synthesize_model(
                    self._provider, self._model, request, seed=key_seed
                )
                if synthesized is not None:
                    self._stats.synthesized += 1
                    return synthesized
            self._stats.flagged += 1
            raise Tier2Miss(
                f"model_call provider={self._provider!r} model={self._model!r} not recorded; "
                f"Tier-2 (a) refuses to synthesize model calls",
            ) from None


class Tier2Replayer(SimulatedEnvironment):
    """Tier-2 environment: tries cache, then synthesis, then flags."""

    def __init__(
        self,
        recording: Recording,
        *,
        synthesizers: Iterable[Synthesizer] | None = None,
        seed: int = 0,
        trust_source_hints: bool | None = None,
    ) -> None:
        self._recording = recording
        self._tier1 = Tier1Replayer.from_recording(recording)
        # Source hints execute code / read files — trust only when explicitly enabled
        # (ADR-0012). Default reads VOLO_TRUST_SOURCE_HINTS so `from_recording` stays safe.
        if trust_source_hints is None:
            trust_source_hints = (
                os.environ.get("VOLO_TRUST_SOURCE_HINTS", "false").lower() == "true"
            )
        self._synthesizers: list[Synthesizer] = list(
            synthesizers
            if synthesizers is not None
            else [
                SourceInformedSynthesizer(trust_source_hints=trust_source_hints),
                OllamaConstrainedSynthesizer(),
            ]
        )
        self._tool_specs = {s.name: s for s in recording.tool_specs}
        self._seed = seed
        self.stats = Tier2Stats()

    @classmethod
    def from_recording(cls, recording: Recording) -> Tier2Replayer:
        return cls(recording)

    def model_provider(self, provider: str = "unknown", model: str = "unknown") -> ModelProvider:
        return _ChainedModelProvider(
            self._tier1.model_provider(provider, model),
            self._synthesizers,
            provider,
            model,
            self._seed,
            self.stats,
        )

    def tool_registry(self) -> ToolRegistry:
        return _ChainedToolRegistry(
            self._tier1.tool_registry(),
            self._synthesizers,
            self._tool_specs,
            self._seed,
            self.stats,
        )
