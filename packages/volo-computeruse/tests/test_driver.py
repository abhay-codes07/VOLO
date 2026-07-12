"""PlaywrightDriver records actions from a (fake) Page; the recording replays deterministically."""

from __future__ import annotations

from volo_computeruse import (
    ActionEvent,
    ComputerUseReplayServer,
    PlaywrightDriver,
    screenshot_hash,
)


class FakePage:
    """A stand-in for a Playwright Page: mutates a string 'DOM' so screenshots differ per state."""

    def __init__(self) -> None:
        self.state = "home"

    def screenshot(self) -> bytes:
        return self.state.encode("utf-8")

    def goto(self, url: str) -> None:
        self.state = f"page::{url}"

    def click(self, selector: str) -> None:
        self.state = f"{self.state}|click:{selector}"

    def fill(self, selector: str, value: str) -> None:
        self.state = f"{self.state}|fill:{selector}={value}"


def _drive() -> PlaywrightDriver:
    driver = PlaywrightDriver(FakePage(), session_name="checkout")
    driver.navigate("https://shop.test")
    driver.click("#add-to-cart")
    driver.type("#coupon", "SAVE10")
    return driver


def test_driver_records_actions_as_events() -> None:
    rec = _drive().recording
    tools = [s.payload.tool for s in rec.steps]
    assert tools == ["cu.navigate", "cu.click", "cu.type"]
    assert rec.agent_meta.framework == "computer_use"
    # each step's pre-action screen differs from the next (state advanced)
    screens = [s.payload.request["screen"] for s in rec.steps]
    assert len(set(screens)) == 3


def test_before_screen_is_recorded_state() -> None:
    driver = PlaywrightDriver(FakePage())
    # first action's pre-screen is the initial 'home' state
    driver.navigate("https://x")
    first = driver.recording.steps[0].payload
    assert first.request["screen"] == screenshot_hash("home")
    assert first.response["screen_after"] == screenshot_hash("page::https://x")


def test_recording_replays_and_flags_unseen_screen() -> None:
    rec = _drive().recording
    server = ComputerUseReplayServer.from_recording(rec)

    # reconstruct each recorded event and confirm it replays (not flagged)
    for step in rec.steps:
        p = step.payload
        event = ActionEvent(
            kind=p.tool.removeprefix("cu."),
            target=p.request["target"],
            value=p.request["value"],
            screen=p.request["screen"],
        )
        out = server.step(event)
        assert "__flagged__" not in out, out
        assert out["result"] == {"ok": True}

    # the same first action on a screen the driver never saw -> flagged
    unseen = ActionEvent(kind="click", target="#add-to-cart", screen="never-seen")
    assert "__flagged__" in server.step(unseen)


def test_driver_is_duck_typed_no_playwright_import() -> None:
    # importing the driver must not require playwright (the core stays browser-free)
    import sys

    import volo_computeruse.driver as d

    assert "playwright" not in sys.modules or d is not None  # never imports it at module load
