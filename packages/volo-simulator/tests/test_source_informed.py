"""Tests for the Tier-2 (b) ``SourceInformedSynthesizer`` (ADR-0009, ADR-0010)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from volo_core import Recording, ToolCallPayload, ToolSpec, cache_key
from volo_simulator import (
    OllamaConstrainedSynthesizer,
    SourceInformedSynthesizer,
    Tier2Miss,
    Tier2Replayer,
)


# A simple in-test shadow we can point a `python:` source_hint at.
def my_search_shadow(request: dict[str, Any]) -> dict[str, Any]:
    return {"hits": [{"title": "Synth", "url": "https://example/" + str(request.get("q", ""))}]}


# ── parsing ──────────────────────────────────────────────────────────────────


def test_abstains_on_no_hint() -> None:
    s = SourceInformedSynthesizer()
    spec = ToolSpec(name="search", output_schema={"type": "object"})
    assert s.synthesize_tool("search", {"q": "x"}, spec, seed=0) is None
    assert s.stats.get("miss_no_hint") == 1


def test_abstains_on_malformed_hint() -> None:
    s = SourceInformedSynthesizer()
    spec = ToolSpec(name="search", output_schema={"type": "object"}, source_hint="garbage")
    assert s.synthesize_tool("search", {"q": "x"}, spec, seed=0) is None
    assert s.stats.get("miss_malformed_hint") == 1


# ── python shadow ────────────────────────────────────────────────────────────


def test_python_shadow_validates_and_returns() -> None:
    s = SourceInformedSynthesizer(trust_source_hints=True)
    spec = ToolSpec(
        name="search",
        output_schema={
            "type": "object",
            "required": ["hits"],
            "properties": {"hits": {"type": "array", "items": {"type": "object"}}},
        },
        source_hint="python:examples.research_agent.agent:search_shadow",
    )
    # Calling search_shadow({"query": "volo"}) returns the canned recorded hits.
    out = s.synthesize_tool("search", {"query": "volo"}, spec, seed=0)
    assert out is not None
    assert "hits" in out and len(out["hits"]) > 0
    assert s.stats.get("hit_python") == 1


def test_python_shadow_abstains_when_validation_fails() -> None:
    """If the callable returns a dict that doesn't match output_schema, abstain."""
    s = SourceInformedSynthesizer(trust_source_hints=True)
    # output_schema requires a `wrong_key` that our shadow doesn't produce.
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object", "required": ["wrong_key"], "properties": {}},
        source_hint="python:examples.research_agent.agent:search_shadow",
    )
    out = s.synthesize_tool("search", {"q": "x"}, spec, seed=0)
    assert out is None
    assert s.stats.get("miss_python_invalid") == 1


def test_python_shadow_abstains_on_import_error() -> None:
    s = SourceInformedSynthesizer(trust_source_hints=True)
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        source_hint="python:nonexistent.module:does_not_matter",
    )
    assert s.synthesize_tool("search", {"q": "x"}, spec, seed=0) is None
    assert s.stats.get("miss_python_error") == 1


# ── fixture file ─────────────────────────────────────────────────────────────


def test_fixture_lookup_by_cache_key(tmp_path: Path) -> None:
    request = {"q": "volo"}
    key = cache_key("fixture", request)
    fixture_path = tmp_path / "search.json"
    fixture_path.write_text(
        json.dumps(
            {
                key: {"hits": [{"title": "Fixture", "url": "u"}]},
            }
        ),
        encoding="utf-8",
    )

    spec = ToolSpec(
        name="search",
        output_schema={"type": "object", "required": ["hits"]},
        source_hint=f"fixture:{fixture_path}",
    )
    s = SourceInformedSynthesizer(trust_source_hints=True)
    out = s.synthesize_tool("search", request, spec, seed=0)
    assert out == {"hits": [{"title": "Fixture", "url": "u"}]}
    assert s.stats.get("hit_fixture") == 1


def test_fixture_abstains_when_key_missing(tmp_path: Path) -> None:
    fixture_path = tmp_path / "search.json"
    fixture_path.write_text(json.dumps({"some-other-key": {}}), encoding="utf-8")

    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        source_hint=f"fixture:{fixture_path}",
    )
    s = SourceInformedSynthesizer(trust_source_hints=True)
    assert s.synthesize_tool("search", {"q": "novel"}, spec, seed=0) is None


# ── openapi ──────────────────────────────────────────────────────────────────

OPENAPI_SAMPLE = {
    "openapi": "3.0.0",
    "info": {"title": "test", "version": "1.0"},
    "paths": {
        "/search": {
            "post": {
                "operationId": "search",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["hits"],
                                    "properties": {
                                        "hits": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["title", "url"],
                                                "properties": {
                                                    "title": {"type": "string", "example": "Hi"},
                                                    "url": {"type": "string", "example": "u"},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


def test_openapi_derives_example_response(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(OPENAPI_SAMPLE), encoding="utf-8")

    spec = ToolSpec(
        name="search",
        output_schema={"type": "object", "required": ["hits"]},
        source_hint=f"openapi:{spec_path}",
    )
    s = SourceInformedSynthesizer(trust_source_hints=True)
    out = s.synthesize_tool("search", {"q": "x"}, spec, seed=0)
    assert out is not None
    assert "hits" in out
    assert s.stats.get("hit_openapi") == 1


def test_openapi_abstains_when_operation_missing(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(OPENAPI_SAMPLE), encoding="utf-8")

    spec = ToolSpec(
        name="not_in_spec",
        output_schema={"type": "object"},
        source_hint=f"openapi:{spec_path}",
    )
    s = SourceInformedSynthesizer(trust_source_hints=True)
    assert s.synthesize_tool("not_in_spec", {}, spec, seed=0) is None


# ── chain order in Tier2Replayer ─────────────────────────────────────────────


class _RaisingOllama:
    """Pretends Ollama is unreachable — proves source-informed runs FIRST."""

    def __init__(self) -> None:
        self.was_called = False

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        self.was_called = True
        raise RuntimeError("should never be called when source-informed succeeds")


def test_source_informed_runs_before_ollama() -> None:
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object", "required": ["hits"]},
        source_hint="python:examples.research_agent.agent:search_shadow",
    )
    r = Recording(tool_specs=[spec])
    r.add_step(
        ToolCallPayload(
            tool="search",
            request={"q": "seen"},
            response={"hits": [{"title": "Old", "url": "u"}]},
        ),
    )

    ollama = _RaisingOllama()
    env = Tier2Replayer(
        r,
        synthesizers=[
            SourceInformedSynthesizer(trust_source_hints=True),
            OllamaConstrainedSynthesizer(provider=ollama),  # would raise if called
        ],
    )
    out = env.tool_registry().call("search", {"q": "novel"})
    assert out is not None and "hits" in out
    assert ollama.was_called is False
    assert env.stats.synthesized == 1
    assert env.stats.flagged == 0


def test_flag_when_all_strategies_abstain() -> None:
    """If both source-informed and Ollama abstain, Tier-2 raises."""
    spec = ToolSpec(name="x", output_schema={"type": "object"})  # no source_hint
    r = Recording(tool_specs=[spec])
    env = Tier2Replayer(
        r,
        synthesizers=[
            SourceInformedSynthesizer(),
            OllamaConstrainedSynthesizer(provider=None),  # no Ollama either
        ],
    )
    with pytest.raises(Tier2Miss):
        env.tool_registry().call("x", {"q": "y"})
    assert env.stats.flagged == 1


# ── security: source_hint trust boundary (ADR-0012) ──────────────────────────


def test_untrusted_python_hint_is_never_executed() -> None:
    """The default (untrusted) synthesizer refuses to import+call a python: hint."""
    s = SourceInformedSynthesizer()  # trust_source_hints defaults to False
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        source_hint="python:examples.research_agent.agent:search_shadow",
    )
    assert s.synthesize_tool("search", {"query": "volo"}, spec, seed=0) is None
    assert s.stats.get("miss_python_untrusted") == 1
    assert s.stats.get("hit_python") is None


def test_untrusted_fixture_read_refused_without_base_dir(tmp_path: Path) -> None:
    request = {"q": "volo"}
    fixture_path = tmp_path / "search.json"
    fixture_path.write_text(
        json.dumps({cache_key("fixture", request): {"hits": []}}),
        encoding="utf-8",
    )
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        source_hint=f"fixture:{fixture_path}",
    )
    s = SourceInformedSynthesizer()  # untrusted, no base_dir → no file reads at all
    assert s.synthesize_tool("search", request, spec, seed=0) is None


def test_untrusted_fixture_confined_to_base_dir(tmp_path: Path) -> None:
    request = {"q": "volo"}
    inside = tmp_path / "search.json"
    inside.write_text(
        json.dumps({cache_key("fixture", request): {"hits": [{"t": 1}]}}),
        encoding="utf-8",
    )
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        # Untrusted hints must be RELATIVE to base_dir (absolute paths are refused; ADR-0012).
        source_hint="fixture:search.json",
    )
    s = SourceInformedSynthesizer(base_dir=tmp_path)
    assert s.synthesize_tool("search", request, spec, seed=0) == {"hits": [{"t": 1}]}


def test_untrusted_fixture_traversal_outside_base_dir_refused(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    secret = tmp_path / "secret.json"
    secret.write_text(
        json.dumps({cache_key("fixture", {"q": "x"}): {"leak": True}}), encoding="utf-8"
    )
    spec = ToolSpec(
        name="search",
        output_schema={"type": "object"},
        source_hint="fixture:../secret.json",  # escapes base via ..
    )
    s = SourceInformedSynthesizer(base_dir=base)
    assert s.synthesize_tool("search", {"q": "x"}, spec, seed=0) is None
