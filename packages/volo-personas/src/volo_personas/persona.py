"""Persona — a seeded, deterministic simulated counterparty (newplan M17).

A ``Persona`` answers an agent's clarifying questions the way a real user (or a sub-agent, or
another agent) might — but deterministically, so multi-turn agents can be tested in CI. Answers
resolve in a fixed order: keyword-matched **facts** first, then an ordered **script** of
fallback lines, then a default. No model call, so a persona is free and reproducible.

Personas serialize to/from JSON so they're shareable packs (the marketplace seed, newplan P6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Persona:
    """A scripted user/counterparty.

    Args:
        name: display name.
        goal: what this persona is trying to get the agent to do (for the transcript/verdict).
        facts: keyword → answer. The first fact whose *key* appears in the question wins, so
            order is significant. This is the persona's knowledge.
        script: ordered fallback answers, consumed one per unmatched question.
        default: what to say when neither a fact nor a script line applies.
        expected: substrings that should appear in the agent's final output if the goal was met.
    """

    name: str
    goal: str = ""
    facts: dict[str, str] = field(default_factory=dict)
    script: list[str] = field(default_factory=list)
    default: str = "I'm not sure — please use your best judgment."
    expected: list[str] = field(default_factory=list)

    def answer(self, question: str, *, script_turn: int) -> str:
        """Resolve the persona's reply to ``question`` (``script_turn`` = # of prior fallbacks)."""
        q = question.lower()
        for keyword, value in self.facts.items():
            if keyword.lower() in q:
                return value
        if script_turn < len(self.script):
            return self.script[script_turn]
        return self.default

    # ---- serialization (persona packs) ----

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "goal": self.goal,
            "facts": dict(self.facts),
            "script": list(self.script),
            "default": self.default,
            "expected": list(self.expected),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Persona:
        if "name" not in data:
            raise ValueError("persona is missing required field 'name'")
        return cls(
            name=str(data["name"]),
            goal=str(data.get("goal", "")),
            facts={str(k): str(v) for k, v in (data.get("facts") or {}).items()},
            script=[str(x) for x in (data.get("script") or [])],
            default=str(data.get("default", "I'm not sure — please use your best judgment.")),
            expected=[str(x) for x in (data.get("expected") or [])],
        )


def goal_satisfied(final_output: Any, persona: Persona) -> bool:
    """True if every ``persona.expected`` marker appears in the agent's final output."""
    if not persona.expected:
        return True
    try:
        blob = json.dumps(final_output, default=str)
    except (TypeError, ValueError):
        blob = str(final_output)
    low = blob.lower()
    return all(marker.lower() in low for marker in persona.expected)


def load_persona(path: Path | str) -> Persona:
    return Persona.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def dump_persona(persona: Persona, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(persona.to_dict(), indent=2) + "\n", encoding="utf-8")
    return target


def default_personas() -> list[Persona]:
    """A small built-in set for demos and tests."""
    return [
        Persona(
            name="decisive-traveler",
            goal="book a one-way flight to Tokyo in economy",
            facts={
                "destination": "Tokyo",
                "class": "economy",
                "one-way or round": "one-way",
                "budget": "under $900",
            },
            script=["Yes, that works.", "Go ahead and book it."],
            expected=["Tokyo"],
        ),
        Persona(
            name="vague-shopper",
            goal="get a gift recommendation and be nudged toward specifics",
            facts={"budget": "around $50", "recipient": "my brother"},
            script=["Hmm, not sure.", "Whatever you think is best."],
            default="I don't really mind.",
        ),
    ]
