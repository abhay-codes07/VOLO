"""Action-event schema for computer-use agents (newplan M31).

A computer-use agent acts on a UI: click, type, scroll, navigate, screenshot. Each action happens
*in a UI state*, so the identity of an action is ``(kind, target, value, screenshot_hash)`` — the
same click on a different screen is a different event. That lets the simulator replay the recorded
outcome for a seen (action, screen) pair and **flag** an unseen one rather than fabricate UI state
(the ADR-0009 invariant, now for pixels).

Events map onto the ordinary Volo Recording as ``tool_call`` steps (tool ``cu.<kind>``), so the
whole simulator/scenario/reliability stack applies — exactly like MCP (ADR-0014).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

ACTION_KINDS: tuple[str, ...] = (
    "click",
    "type",
    "key",
    "scroll",
    "navigate",
    "screenshot",
    "wait",
)

TOOL_PREFIX = "cu."


def screenshot_hash(data: bytes | str) -> str:
    """A stable, short fingerprint of a UI screenshot (or any DOM/state serialization)."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()[:32]


@dataclass(frozen=True)
class ActionEvent:
    """One action an agent takes on a UI, in a given screen state."""

    kind: str
    target: str = ""  # CSS selector, element id, or "x,y" coordinates
    value: str = ""  # typed text, url, key name, scroll delta…
    screen: str | None = None  # screenshot_hash of the UI *before* the action

    def __post_init__(self) -> None:
        if self.kind not in ACTION_KINDS:
            raise ValueError(f"unknown action kind {self.kind!r}; known: {list(ACTION_KINDS)}")

    def key(self) -> tuple[str, dict[str, Any]]:
        """Map to the ``(tool, request)`` identity Volo caches on — keyed on the screen too."""
        return f"{TOOL_PREFIX}{self.kind}", {
            "target": self.target,
            "value": self.value,
            "screen": self.screen,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "target": self.target,
            "value": self.value,
            "screen": self.screen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionEvent:
        if "kind" not in data:
            raise ValueError("action event is missing 'kind'")
        return cls(
            kind=str(data["kind"]),
            target=str(data.get("target", "")),
            value=str(data.get("value", "")),
            screen=data.get("screen"),
        )
