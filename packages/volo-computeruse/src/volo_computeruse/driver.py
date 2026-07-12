"""Live driver that feeds ``ComputerUseRecorder`` from a real browser (post-v5.0; ADR-0034).

M31 shipped the transport-free core (``ActionEvent`` / recorder / replay). ``PlaywrightDriver`` is
the live transport — the analog of the MCP stdio adapter: it wraps a Playwright ``Page``, performs
each action on the real page, hashes the screen *before* and *after*, and records an
``ActionEvent``. The recording then replays deterministically offline via
``ComputerUseReplayServer`` — flagging any (action, screen) it never saw.

The driver is **duck-typed** over the Page: it never imports ``playwright`` and only calls the
methods it needs (``screenshot``, ``goto``, ``click``, ``fill``), so a real Playwright page drives
it in production and a fake page drives it in tests — no browser needed in CI. ``playwright`` is an
optional extra (``volo-computeruse[playwright]``).
"""

from __future__ import annotations

from typing import Any, Protocol

from volo_computeruse.events import ActionEvent, screenshot_hash
from volo_computeruse.recorder import ComputerUseRecorder


class Page(Protocol):
    """The slice of the Playwright sync ``Page`` API the driver uses."""

    def screenshot(self) -> bytes: ...
    def goto(self, url: str) -> Any: ...
    def click(self, selector: str) -> Any: ...
    def fill(self, selector: str, value: str) -> Any: ...


class PlaywrightDriver:
    """Drive a browser page and record every action as an ``ActionEvent``."""

    def __init__(
        self,
        page: Page,
        *,
        recorder: ComputerUseRecorder | None = None,
        session_name: str = "playwright",
    ) -> None:
        self._page = page
        self.recorder = recorder or ComputerUseRecorder(session_name=session_name)

    def _screen(self) -> str:
        # Hash the current screenshot; a DOM serialization would work identically.
        return screenshot_hash(self._page.screenshot())

    def _record(
        self, kind: str, *, target: str, value: str, before: str, result: dict[str, Any]
    ) -> str:
        after = self._screen()
        self.recorder.record(
            ActionEvent(kind=kind, target=target, value=value, screen=before),
            result=result,
            screen_after=after,
        )
        return after

    def navigate(self, url: str) -> str:
        """Go to ``url`` and record it; returns the resulting screen hash."""
        before = self._screen()
        self._page.goto(url)
        return self._record("navigate", target="", value=url, before=before, result={"ok": True})

    def click(self, selector: str) -> str:
        before = self._screen()
        self._page.click(selector)
        return self._record("click", target=selector, value="", before=before, result={"ok": True})

    def type(self, selector: str, text: str) -> str:
        before = self._screen()
        self._page.fill(selector, text)
        return self._record("type", target=selector, value=text, before=before, result={"ok": True})

    @property
    def recording(self):  # type: ignore[no-untyped-def]
        return self.recorder.recording

    def save(self, path: Any = None) -> Any:
        return self.recorder.save(path)
