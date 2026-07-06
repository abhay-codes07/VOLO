"""A multi-turn agent that asks the user clarifying questions before acting.

Given an ambiguous "book me a flight" task, it asks for the destination and cabin class via the
``ask_user`` tool, then composes a booking. Run against a persona (``volo persona run``), the
questions are answered deterministically from the persona's facts/script — so a multi-turn agent
becomes a reproducible CI test.
"""

from __future__ import annotations

from typing import Any

from volo_core import get_active_environment


def _ask(question: str) -> str:
    env = get_active_environment()
    if env is None:
        raise RuntimeError("no active Volo environment")
    reply = env.tool_registry().call("ask_user", {"question": question})
    return str(reply.get("answer", ""))


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ask for the missing details, then 'book'. Returns a booking summary."""
    destination = _ask("What is your destination?")
    cabin = _ask("Which cabin class would you like?")
    trip = _ask("Is this one-way or round-trip?")
    return {
        "booked": True,
        "summary": f"{trip} flight to {destination} in {cabin}",
        "destination": destination,
        "cabin": cabin,
    }
