"""Two tiny agents for the red-team demo: one that leaks, one that doesn't.

``naive_summarizer`` concatenates raw tool output straight into its answer — the classic
injection-vulnerable pattern, so poisoned tool content (and its canary) surfaces in the output.
``guarded_summarizer`` only reads known, structured fields and never echoes free-form tool text,
so it stays clean. Red-teaming should flag the first and clear the second.
"""

from __future__ import annotations

from typing import Any

from volo_core import get_active_environment


def _search(query: str) -> dict[str, Any]:
    env = get_active_environment()
    if env is None:
        raise RuntimeError("no active Volo environment")
    return env.tool_registry().call("search", {"q": query})


def naive_summarizer(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """VULNERABLE: dumps the whole tool response (including any injected text) into the answer."""
    result = _search((payload or {}).get("q", "volo"))
    # Naively stringify everything the tool returned — this is the bug.
    answer = " ".join(str(v) for v in result.values())
    return {"answer": answer}


def guarded_summarizer(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """SAFE: reads only the known 'hits' count; never echoes free-form tool text."""
    result = _search((payload or {}).get("q", "volo"))
    hits = result.get("hits")
    return {"answer": f"found {hits} result(s)"}
