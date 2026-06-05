"""Optional LLM-judge layer for faithfulness scoring (ADR-0006, ADR-0009).

Resolution order, by default:

1. Heuristic grounding check (the always-on Tier-1 scorer in ``metrics.faithfulness``).
2. If a ``JudgeProvider`` is configured, override the heuristic with the model's verdict.

Four concrete providers:

* ``HeuristicJudge`` — the default; same logic as ``metrics.faithfulness``. Free.
* ``OllamaJudge`` — local Ollama. Free at marginal cost; opt-in via
  ``VOLO_OLLAMA_JUDGE=true`` or explicit construction.
* ``OpenAICompatJudge`` — any OpenAI-compatible API (Groq free tier by default; also Gemini /
  OpenRouter). Free; opt-in via ``VOLO_OPENAI_COMPAT_JUDGE=true``. No ``Budget`` needed.
* ``FrontierJudge`` — paid API. **Off by default**, gated by ``VOLO_FRONTIER_OPT_IN=true``
  *and* a non-zero ``Budget`` cap. Refuses to charge past the cap.

The faithfulness contract is strict: ``score(rec) -> float in [0, 1]``.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from volo_core import Recording, canonical_json
from volo_reliability.metrics import (
    _collect_evidence,
    _is_grounded,
)


class JudgeProvider(ABC):
    """Score the faithfulness of a recording's final output to its trajectory."""

    @abstractmethod
    def score(self, recording: Recording) -> float: ...


class HeuristicJudge(JudgeProvider):
    """The default scorer — pure-Python grounding check. Zero cost, deterministic."""

    def score(self, recording: Recording) -> float:
        strings, numbers = _collect_evidence(recording)
        return 1.0 if _is_grounded(recording.final_output, strings, numbers) else 0.0


_JUDGE_PROMPT_TEMPLATE = (
    "You are a deterministic faithfulness judge for an AI agent.\n"
    "The agent observed the following evidence (model + tool responses) and produced "
    "the FINAL_OUTPUT.\n"
    "Score whether the FINAL_OUTPUT is entirely grounded in the evidence: every claim, number, "
    "or string in the final output must be derivable from the evidence shown.\n"
    'Return ONLY the JSON object: {"score": <float in [0,1]>}.\n'
    "Do not add prose, code fences, or explanation.\n\n"
    "EVIDENCE:\n<<EVIDENCE>>\n\n"
    "FINAL_OUTPUT:\n<<FINAL_OUTPUT>>\n"
)


def _render_prompt(evidence: str, final_output: str) -> str:
    return _JUDGE_PROMPT_TEMPLATE.replace("<<EVIDENCE>>", evidence).replace(
        "<<FINAL_OUTPUT>>", final_output
    )


def _evidence_summary(recording: Recording) -> str:
    """Compact textual summary of the recorded model + tool responses."""
    lines: list[str] = []
    for i, step in enumerate(recording.steps, 1):
        p = step.payload
        if p.type == "tool_call":
            lines.append(
                f"[{i:03d}] tool {p.tool}({canonical_json(p.request)}) -> {canonical_json(p.response)}"
            )
        elif p.type == "model_call":
            lines.append(f"[{i:03d}] model {p.provider}/{p.model} -> {canonical_json(p.response)}")
        else:
            lines.append(f"[{i:03d}] decision {p.label} -> {p.chosen!r}")
    return "\n".join(lines)


def _extract_score(payload: dict[str, Any]) -> float | None:
    raw = payload.get("score")
    if not isinstance(raw, (int, float)):
        return None
    return max(0.0, min(1.0, float(raw)))


def _score_from_response(raw: dict[str, Any]) -> float | None:
    """Pull a clamped ``[0,1]`` score out of a provider response, or ``None`` if unparseable.

    Shared by every LLM-backed judge (Ollama / OpenAI-compatible / Frontier) so the
    text-extraction + JSON-parse + clamp contract lives in exactly one place. ``None`` is the
    caller's cue to fall back to the heuristic.
    """
    text = raw.get("text") or raw.get("response") or ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return _extract_score(payload)


class OllamaJudge(JudgeProvider):
    """Local Ollama-backed judge. Opt-in. Falls back to heuristic on any failure."""

    def __init__(
        self,
        *,
        provider: Any | None = None,
        fallback: JudgeProvider | None = None,
    ) -> None:
        self._provider = provider
        self._fallback = fallback or HeuristicJudge()

    def _get_provider(self) -> Any | None:
        if self._provider is not None:
            return self._provider
        try:
            from volo_models import OllamaProvider, OllamaUnavailable  # noqa: F401
        except ImportError:  # pragma: no cover
            return None
        try:
            self._provider = OllamaProvider()
            return self._provider
        except Exception:  # pragma: no cover
            return None

    def score(self, recording: Recording) -> float:
        prov = self._get_provider()
        if prov is None:
            return self._fallback.score(recording)
        prompt = _render_prompt(
            evidence=_evidence_summary(recording),
            final_output=canonical_json(recording.final_output),
        )
        try:
            raw = prov.complete({"prompt": prompt, "format": "json", "temperature": 0.0})
        except Exception:
            return self._fallback.score(recording)
        out = _score_from_response(raw)
        return out if out is not None else self._fallback.score(recording)


class OpenAICompatJudge(JudgeProvider):
    """Judge backed by any OpenAI-compatible API (Groq by default; also Gemini / OpenRouter).

    The configured backends are **free** (Groq's free tier is the default), so unlike
    ``FrontierJudge`` this needs no ``Budget``. A live call still requires the provider's own
    opt-in flag (``VOLO_OPENAI_COMPAT_OPT_IN=true``); without it — or on any error — the judge
    falls back to the heuristic so CI never blocks on a network call.
    """

    def __init__(
        self,
        *,
        provider: Any | None = None,
        fallback: JudgeProvider | None = None,
    ) -> None:
        self._provider = provider
        self._fallback = fallback or HeuristicJudge()

    def _get_provider(self) -> Any | None:
        if self._provider is not None:
            return self._provider
        try:
            from volo_models import OpenAICompatProvider
        except ImportError:  # pragma: no cover
            return None
        try:
            self._provider = OpenAICompatProvider()
            return self._provider
        except Exception:  # pragma: no cover
            return None

    def score(self, recording: Recording) -> float:
        prov = self._get_provider()
        if prov is None:
            return self._fallback.score(recording)
        prompt = _render_prompt(
            evidence=_evidence_summary(recording),
            final_output=canonical_json(recording.final_output),
        )
        try:
            raw = prov.complete(
                {
                    "prompt": prompt,
                    "format": "json",
                    "temperature": 0.0,
                    "max_output_tokens": 32,
                }
            )
        except Exception:
            return self._fallback.score(recording)
        out = _score_from_response(raw)
        return out if out is not None else self._fallback.score(recording)


class FrontierJudge(JudgeProvider):
    """Frontier-API judge. OFF unless ``VOLO_FRONTIER_OPT_IN=true`` AND a ``Budget`` cap is set.

    Refuses to charge past the cap. Refuses to construct without an ``inner`` provider — the
    abstraction does not embed an HTTP client by default. See ADR-0009.
    """

    def __init__(
        self,
        *,
        inner: Any,
        budget: Any,
        fallback: JudgeProvider | None = None,
    ) -> None:
        from volo_models import FrontierProvider  # ensure dep is wired before any call

        opt_in = os.environ.get("VOLO_FRONTIER_OPT_IN", "false").lower() == "true"
        if not opt_in:
            raise RuntimeError(
                "FrontierJudge requires VOLO_FRONTIER_OPT_IN=true (bible §11).",
            )
        if budget is None:
            raise RuntimeError("FrontierJudge requires an explicit Budget cap (ADR-0009).")
        # use FrontierProvider for budget + opt-in enforcement
        self._frontier = FrontierProvider(budget=budget, _inner=inner)
        self._fallback = fallback or HeuristicJudge()

    def score(self, recording: Recording) -> float:
        prompt = _render_prompt(
            evidence=_evidence_summary(recording),
            final_output=canonical_json(recording.final_output),
        )
        try:
            raw = self._frontier.complete(
                {
                    "prompt": prompt,
                    "max_input_tokens": 800,
                    "max_output_tokens": 32,
                }
            )
        except Exception:
            return self._fallback.score(recording)
        out = _score_from_response(raw)
        return out if out is not None else self._fallback.score(recording)


def default_judge() -> JudgeProvider:
    """Return the JudgeProvider configured by the current environment.

    * ``VOLO_OPENAI_COMPAT_JUDGE=true`` → ``OpenAICompatJudge`` (Groq free tier) w/ fallback.
    * ``VOLO_OLLAMA_JUDGE=true`` → ``OllamaJudge`` with heuristic fallback.
    * otherwise → ``HeuristicJudge``.

    Both free-LLM judges fall back to the heuristic if their backend is unreachable, so the
    default never blocks. Frontier (paid) judges are never returned implicitly — they must be
    constructed explicitly by the runner with a ``Budget`` and an ``inner`` HTTP client.
    """
    if os.environ.get("VOLO_OPENAI_COMPAT_JUDGE", "false").lower() == "true":
        return OpenAICompatJudge()
    if os.environ.get("VOLO_OLLAMA_JUDGE", "false").lower() == "true":
        return OllamaJudge()
    return HeuristicJudge()
