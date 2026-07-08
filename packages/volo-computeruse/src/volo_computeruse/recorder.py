"""ComputerUseRecorder — capture a computer-use session as an ordinary Volo Recording (M31).

Feed each action the agent took, the result the UI returned, and the screenshot hash *after* the
action. Each becomes a ``tool_call`` step (tool ``cu.<kind>``) keyed on the pre-action screen, so
replay reproduces the recorded outcome for the same (action, screen) and flags anything else.
A real driver (Playwright/pyautogui) feeds this recorder; slice 1 ships the transport-free core.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_computeruse.events import ActionEvent
from volo_core import Recording
from volo_core.recording import ToolCallPayload
from volo_sdk import Recorder


class ComputerUseRecorder:
    def __init__(
        self, *, session_name: str = "computer-use", recorder: Recorder | None = None
    ) -> None:
        self._recorder = recorder or Recorder(agent_name=session_name, framework="computer_use")
        self.n_actions = 0

    def record(
        self,
        event: ActionEvent,
        *,
        result: dict[str, Any] | None = None,
        screen_after: str | None = None,
    ) -> None:
        """Append one action + its UI outcome to the recording."""
        tool, request = event.key()
        response = {"result": result or {}, "screen_after": screen_after}
        self._recorder.record_step(ToolCallPayload(tool=tool, request=request, response=response))
        self.n_actions += 1

    @property
    def recording(self) -> Recording:
        return self._recorder.recording

    def save(self, path: Path | str | None = None) -> Path:
        return self._recorder.save(path)
