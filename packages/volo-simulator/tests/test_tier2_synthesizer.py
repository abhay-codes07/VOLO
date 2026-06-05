"""Tier-2 synthesizer tests (ADR-0009).

These tests use a stub ``ModelProvider`` so they don't require a running Ollama daemon.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from volo_core import (
    ModelCallPayload,
    Recording,
    ToolCallPayload,
    ToolSpec,
)
from volo_core.interfaces import ModelProvider
from volo_simulator import (
    OllamaConstrainedSynthesizer,
    Tier2Miss,
    Tier2Replayer,
)


class _ScriptedProvider(ModelProvider):
    """Pretend-Ollama: returns canned JSON strings in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(dict(request))
        if not self._responses:
            return {"text": "{}"}
        return {"text": self._responses.pop(0)}


# ── helpers ──────────────────────────────────────────────────────────────────


def _recording_with_spec() -> Recording:
    r = Recording(
        tool_specs=[
            ToolSpec(
                name="search",
                description="Web search returning a list of hits.",
                input_schema={
                    "type": "object",
                    "required": ["q"],
                    "properties": {"q": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "required": ["hits"],
                    "properties": {
                        "hits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "url"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            ),
        ],
    )
    # Seed one recorded call so Tier-1 has at least one hit; synthesizer handles the un-recorded one.
    r.add_step(
        ToolCallPayload(
            tool="search",
            request={"q": "volo"},
            response={"hits": [{"title": "Volo", "url": "https://example/volo"}]},
        ),
    )
    return r


# ── tests ────────────────────────────────────────────────────────────────────


def test_validator_passes_well_shaped_object() -> None:
    synth = OllamaConstrainedSynthesizer(
        provider=_ScriptedProvider([json.dumps({"hits": [{"title": "A", "url": "u"}]})]),
    )
    spec = _recording_with_spec().tool_specs[0]
    out = synth.synthesize_tool("search", {"q": "novel"}, spec, seed=0)
    assert out == {"hits": [{"title": "A", "url": "u"}]}
    assert synth.stats == {"hit": 1}


def test_validator_rejects_missing_required_field() -> None:
    # Two attempts: first is missing 'hits', second is well-shaped.
    synth = OllamaConstrainedSynthesizer(
        provider=_ScriptedProvider(
            [
                json.dumps({"hots": []}),
                json.dumps({"hits": [{"title": "A", "url": "u"}]}),
            ]
        ),
    )
    spec = _recording_with_spec().tool_specs[0]
    out = synth.synthesize_tool("search", {"q": "novel"}, spec, seed=0)
    assert out == {"hits": [{"title": "A", "url": "u"}]}


def test_validator_extracts_json_from_text_block() -> None:
    synth = OllamaConstrainedSynthesizer(
        provider=_ScriptedProvider(
            [
                "Sure! Here you go:\n"
                + json.dumps({"hits": [{"title": "A", "url": "u"}]})
                + "\nEnjoy.",
            ]
        ),
    )
    spec = _recording_with_spec().tool_specs[0]
    out = synth.synthesize_tool("search", {"q": "novel"}, spec, seed=0)
    assert out is not None and "hits" in out


def test_no_schema_returns_none() -> None:
    synth = OllamaConstrainedSynthesizer(provider=_ScriptedProvider([]))
    out = synth.synthesize_tool("anything", {"x": 1}, None, seed=0)
    assert out is None
    assert synth.stats == {"miss_no_schema": 1}


def test_invalid_attempts_exhausted_returns_none() -> None:
    synth = OllamaConstrainedSynthesizer(
        provider=_ScriptedProvider(["", "not json at all", "{}"]),
        max_attempts=2,
    )
    spec = _recording_with_spec().tool_specs[0]
    out = synth.synthesize_tool("search", {"q": "novel"}, spec, seed=0)
    assert out is None
    assert synth.stats == {"miss_invalid_json": 1}


# ── Tier2Replayer integration ────────────────────────────────────────────────


def test_tier2_serves_cache_hits_unchanged() -> None:
    rec = _recording_with_spec()
    synth = OllamaConstrainedSynthesizer(provider=_ScriptedProvider([]))
    env = Tier2Replayer(rec, synthesizers=[synth])
    tools = env.tool_registry()
    # The recorded q=volo input is a cache hit — never reaches synthesizer.
    assert tools.call("search", {"q": "volo"}) == {
        "hits": [{"title": "Volo", "url": "https://example/volo"}]
    }
    assert env.stats.cache_hits == 1
    assert env.stats.synthesized == 0
    assert env.stats.flagged == 0


def test_tier2_synthesizes_on_miss() -> None:
    rec = _recording_with_spec()
    synth = OllamaConstrainedSynthesizer(
        provider=_ScriptedProvider([json.dumps({"hits": [{"title": "Synth", "url": "u"}]})]),
    )
    env = Tier2Replayer(rec, synthesizers=[synth])
    tools = env.tool_registry()
    out = tools.call("search", {"q": "never seen"})
    assert out == {"hits": [{"title": "Synth", "url": "u"}]}
    assert env.stats.synthesized == 1
    assert env.stats.flagged == 0


def test_tier2_flags_on_unknown_with_no_spec() -> None:
    r = Recording()  # no specs, no recorded calls
    env = Tier2Replayer(
        r,
        synthesizers=[OllamaConstrainedSynthesizer(provider=_ScriptedProvider([]))],
    )
    tools = env.tool_registry()
    with pytest.raises(Tier2Miss):
        tools.call("search", {"q": "x"})
    assert env.stats.flagged == 1


def test_tier2_flags_model_call_on_unrecorded_input() -> None:
    """Tier-2 (a) refuses to synthesize model calls (ADR-0009)."""
    r = Recording()
    r.add_step(
        ModelCallPayload(
            provider="echo",
            model="echo-1",
            request={"prompt": "known"},
            response={"text": "known", "stop_reason": "end_turn"},
        ),
    )
    env = Tier2Replayer(
        r, synthesizers=[OllamaConstrainedSynthesizer(provider=_ScriptedProvider([]))]
    )
    prov = env.model_provider("echo", "echo-1")
    # cache hit
    assert prov.complete({"prompt": "known"}) == {"text": "known", "stop_reason": "end_turn"}
    # miss → flagged
    with pytest.raises(Tier2Miss):
        prov.complete({"prompt": "novel"})
    assert env.stats.flagged == 1
