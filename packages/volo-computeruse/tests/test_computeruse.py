"""Computer-use: record → replay by (action, screen); unseen screens flag, never fabricate."""

from __future__ import annotations

from pathlib import Path

import pytest

from volo_computeruse import (
    ActionEvent,
    ComputerUseRecorder,
    ComputerUseReplayServer,
    screenshot_hash,
)


def test_screenshot_hash_is_stable_and_short() -> None:
    h = screenshot_hash("<dom>home</dom>")
    assert h == screenshot_hash(b"<dom>home</dom>")
    assert len(h) == 32
    assert h != screenshot_hash("<dom>other</dom>")


def test_action_event_validation_and_key() -> None:
    e = ActionEvent(kind="click", target="#buy", screen="scr1")
    tool, request = e.key()
    assert tool == "cu.click"
    assert request == {"target": "#buy", "value": "", "screen": "scr1"}
    with pytest.raises(ValueError, match="unknown action kind"):
        ActionEvent(kind="teleport")


def _recorded_session() -> ComputerUseRecorder:
    rec = ComputerUseRecorder(session_name="checkout")
    home, cart = screenshot_hash("home"), screenshot_hash("cart")
    rec.record(
        ActionEvent(kind="click", target="#add-to-cart", screen=home),
        result={"ok": True},
        screen_after=cart,
    )
    rec.record(
        ActionEvent(kind="type", target="#coupon", value="SAVE10", screen=cart),
        result={"applied": True},
        screen_after=cart,
    )
    return rec


def test_record_maps_to_tool_calls() -> None:
    rec = _recorded_session()
    tools = [s.payload.tool for s in rec.recording.steps]
    assert tools == ["cu.click", "cu.type"]
    assert rec.recording.agent_meta.framework == "computer_use"
    assert rec.n_actions == 2


def test_replay_reproduces_recorded_outcome() -> None:
    rec = _recorded_session()
    server = ComputerUseReplayServer.from_recording(rec.recording)
    home = screenshot_hash("home")
    out = server.step(ActionEvent(kind="click", target="#add-to-cart", screen=home))
    assert out["result"] == {"ok": True}
    assert out["screen_after"] == screenshot_hash("cart")


def test_same_action_different_screen_flags() -> None:
    rec = _recorded_session()
    server = ComputerUseReplayServer.from_recording(rec.recording)
    # the click was recorded on the home screen; the same click on an unseen screen must flag
    out = server.step(ActionEvent(kind="click", target="#add-to-cart", screen="unseen-screen"))
    assert "__flagged__" in out
    assert "no recorded outcome" in out["__flagged__"]


def test_unseen_action_flags() -> None:
    rec = _recorded_session()
    server = ComputerUseReplayServer.from_recording(rec.recording)
    out = server.step(ActionEvent(kind="click", target="#never", screen=screenshot_hash("home")))
    assert "__flagged__" in out


def test_save_roundtrip(tmp_path: Path) -> None:
    from volo_core import Recording

    path = _recorded_session().save(tmp_path / "session.json")
    loaded = Recording.from_json(path.read_text(encoding="utf-8"))
    assert len(loaded.steps) == 2 and loaded.agent_meta.framework == "computer_use"


def test_event_dict_roundtrip() -> None:
    e = ActionEvent(kind="navigate", value="https://x", screen="s")
    assert ActionEvent.from_dict(e.to_dict()) == e
