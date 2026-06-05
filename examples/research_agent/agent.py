"""A 3-step deterministic "research agent" with rich JSON tool returns.

No external services — the ``_FakeWeb`` registry returns canned answers for the seeded
queries. This is the live-mode behavior; Tier-2's constrained synthesizer is supposed to
produce schema-valid responses for un-recorded queries via Ollama.

Trajectory: ``decision -> tool_call search -> tool_call fetch``.

The agent intentionally does not call the model at the end — its job is research and the
final output is composed from tool returns. This keeps Tier-2 (a) able to drive the agent
fully on un-recorded queries (per ADR-0009, Tier-2 (a) refuses to synthesize model calls).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from volo_core import DecisionPayload, ToolSpec, get_active_recorder
from volo_core.interfaces import ToolRegistry
from volo_sdk import ToolRegistryProxy

TOOLS_JSON_PATH = Path(__file__).resolve().parent / "tools.json"


def tool_specs() -> list[ToolSpec]:
    """Load the declared tool schemas as ``ToolSpec`` instances."""
    data = json.loads(TOOLS_JSON_PATH.read_text(encoding="utf-8"))
    return [
        ToolSpec(
            name=t["name"],
            description=t.get("description"),
            input_schema=t.get("input_schema"),
            output_schema=t.get("output_schema"),
            source_hint=t.get("source_hint"),
        )
        for t in data["tools"]
    ]


class _FakeWeb(ToolRegistry):
    """A deterministic stub for the search + fetch tools."""

    _SEARCH: ClassVar[dict[str, list[dict[str, str]]]] = {
        "volo": [
            {
                "title": "Volo — flight simulator for AI agents",
                "url": "https://volo.dev/",
                "snippet": "Record once. Replay deterministically.",
            },
            {
                "title": "Latin volo",
                "url": "https://en.wiktionary.org/wiki/volo",
                "snippet": "Latin: I fly.",
            },
        ],
        "claude code": [
            {
                "title": "Claude Code — Anthropic",
                "url": "https://docs.claude.com/en/docs/claude-code",
                "snippet": "Agentic coding.",
            },
        ],
    }
    _FETCH: ClassVar[dict[str, dict[str, str]]] = {
        "https://volo.dev/": {
            "title": "Volo — flight simulator for AI agents",
            "body": "Test agents like software. Record, replay, score, ship.",
        },
        "https://en.wiktionary.org/wiki/volo": {
            "title": "volo — Wiktionary",
            "body": "Latin first-person singular present indicative of volō: I fly.",
        },
        "https://docs.claude.com/en/docs/claude-code": {
            "title": "Claude Code",
            "body": "Anthropic's agentic coding CLI.",
        },
    }

    def call(self, tool: str, request: dict[str, Any]) -> dict[str, Any]:
        if tool == "search":
            return search_shadow(request)
        if tool == "fetch":
            return fetch_shadow(request)
        raise KeyError(f"unknown tool: {tool!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Pure-function shadows — Tier-2 (b) source_hint targets
#
# These are intentionally module-level callables with signature ``(request: dict) -> dict``
# so the SourceInformedSynthesizer can import + call them directly without instantiating a
# class. They share state with ``_FakeWeb`` (the registries are class-level constants).
# ─────────────────────────────────────────────────────────────────────────────


def search_shadow(request: dict[str, Any]) -> dict[str, Any]:
    """Pure-function shadow of the ``search`` tool — used by Tier-2 (b)."""
    q = str(request.get("query", ""))
    return {"hits": list(_FakeWeb._SEARCH.get(q, []))}


def fetch_shadow(request: dict[str, Any]) -> dict[str, Any]:
    """Pure-function shadow of the ``fetch`` tool — used by Tier-2 (b)."""
    url = str(request.get("url", ""))
    page = _FakeWeb._FETCH.get(url)
    if page is None:
        return {"title": "Not found", "body": ""}
    return dict(page)


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the research agent.

    Args:
        payload: ``{"query": "<text>"}`` — anything truthy. Defaults to ``{"query": "volo"}``.

    Returns:
        ``{"query": ..., "headline": <title of first hit>, "snippet": <fetched body>}``.
    """
    payload = payload or {}
    query = str(payload.get("query", "volo"))

    rec = get_active_recorder()
    if rec is not None:
        rec.record_step(
            DecisionPayload(label="plan_research", chosen=f"search '{query}' then fetch first hit")
        )

    tools = ToolRegistryProxy(_FakeWeb())

    search = tools.call("search", {"query": query})
    hits = search.get("hits", [])
    if not hits:
        return {"query": query, "headline": None, "snippet": None}

    first = hits[0]
    page = tools.call("fetch", {"url": first["url"]})

    return {
        "query": query,
        "headline": first["title"],
        "snippet": page["body"],
    }
