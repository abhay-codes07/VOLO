"""ComputerUseReplayServer — replay a recorded UI session, flag on unseen (action, screen) (M31).

Point a computer-use agent's action loop at this instead of a live browser: a recorded action on
a recorded screen replays the recorded outcome; anything unseen returns a flagged miss
(``__flagged__``) rather than a fabricated UI state — the ADR-0009 invariant for pixels. Backed by
any ``SimulatedEnvironment`` (Tier-1 by default), so it inherits the whole simulator stack.
"""

from __future__ import annotations

from typing import Any

from volo_computeruse.events import ActionEvent
from volo_core import Recording
from volo_core.interfaces import SimulatedEnvironment, ToolRegistry
from volo_simulator import ReplayMiss, Tier1Replayer


class ComputerUseReplayServer:
    def __init__(self, env: SimulatedEnvironment) -> None:
        self._tools: ToolRegistry = env.tool_registry()

    @classmethod
    def from_recording(cls, recording: Recording) -> ComputerUseReplayServer:
        return cls(Tier1Replayer.from_recording(recording))

    def step(self, event: ActionEvent) -> dict[str, Any]:
        """Return the recorded outcome for ``event`` (``{result, screen_after}``), or a flag."""
        tool, request = event.key()
        try:
            return self._tools.call(tool, request)
        except ReplayMiss as exc:
            return {
                "__flagged__": (
                    f"no recorded outcome for {event.kind} on this screen "
                    f"(target={event.target!r}, screen={event.screen}). {exc}"
                )
            }
