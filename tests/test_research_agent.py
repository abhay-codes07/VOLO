"""e2e: research_agent records 4 steps and replays bit-identically; Tier-2 handles unseen queries."""

from __future__ import annotations

import json
from typing import Any

from examples.research_agent import run, tool_specs

from volo_core import Recording, current_environment, current_recorder
from volo_core.interfaces import ModelProvider
from volo_sdk import Recorder, RecorderConfig
from volo_simulator import (
    OllamaConstrainedSynthesizer,
    Tier1Replayer,
    Tier2Miss,
    Tier2Replayer,
)


def _record(query: str = "volo") -> Recording:
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    rec.recording.tool_specs = tool_specs()
    with current_recorder(rec):
        rec.set_final_output(run({"query": query}))
    return rec.recording


def test_records_three_step_trajectory() -> None:
    r = _record()
    types = [s.type for s in r.steps]
    assert types == ["decision", "tool_call", "tool_call"]


def test_tool_specs_loaded_from_json() -> None:
    specs = tool_specs()
    names = {s.name for s in specs}
    assert names == {"search", "fetch"}
    search = next(s for s in specs if s.name == "search")
    assert search.output_schema is not None
    assert "hits" in (search.output_schema.get("required") or [])


def test_tier1_replay_is_bit_identical() -> None:
    baseline = _record("volo")
    env = Tier1Replayer.from_recording(baseline)
    with current_environment(env):
        replayed = run({"query": "volo"})
    assert replayed["headline"] == "Volo — flight simulator for AI agents"


# ── Tier-2 synthesis on un-recorded inputs ───────────────────────────────────


class _ScriptedOllama(ModelProvider):
    """Returns canned schema-valid JSON for unseen search/fetch inputs."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(dict(request))
        # The prompt embeds the tool name; route by it.
        prompt = str(request.get("prompt", ""))
        if "TOOL: search" in prompt:
            return {
                "text": json.dumps(
                    {
                        "hits": [{"title": "Synth", "url": "https://example/synth"}],
                    }
                )
            }
        if "TOOL: fetch" in prompt:
            return {"text": json.dumps({"title": "Synth", "body": "synthesized body"})}
        return {"text": "{}"}


def test_tier2_synthesizes_unseen_query() -> None:
    baseline = _record("volo")
    env = Tier2Replayer(
        baseline,
        synthesizers=[OllamaConstrainedSynthesizer(provider=_ScriptedOllama())],
    )
    with current_environment(env):
        out = run({"query": "completely novel query"})
    assert out["headline"] == "Synth"
    assert env.stats.synthesized >= 2  # search + fetch both synthesized
    assert env.stats.flagged == 0


def test_tier2_flags_when_synth_returns_nothing() -> None:
    """If the synthesizer can't satisfy a schema, Tier-2 raises rather than hallucinating."""
    baseline = _record("volo")
    # Use a provider that always returns empty so synthesis fails.
    empty_provider = _ScriptedOllama()
    empty_provider.complete = lambda request: {"text": ""}  # type: ignore[method-assign]
    env = Tier2Replayer(
        baseline,
        synthesizers=[OllamaConstrainedSynthesizer(provider=empty_provider)],
    )
    import pytest

    with pytest.raises(Tier2Miss), current_environment(env):
        run({"query": "unseen"})
