"""`volo cu inspect|replay` — computer-use recording CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app
from volo_computeruse import ActionEvent, ComputerUseRecorder, screenshot_hash

runner = CliRunner()


def _recording(tmp_path: Path) -> Path:
    rec = ComputerUseRecorder(session_name="s")
    home, cart = screenshot_hash("home"), screenshot_hash("cart")
    rec.record(
        ActionEvent(kind="click", target="#buy", screen=home),
        result={"ok": True},
        screen_after=cart,
    )
    path = tmp_path / "cu.json"
    rec.save(path)
    return path


def test_inspect(tmp_path: Path) -> None:
    res = runner.invoke(app, ["cu", "inspect", str(_recording(tmp_path))])
    assert res.exit_code == 0, res.output
    assert "cu.click" not in res.output  # inspect strips the prefix
    assert "click" in res.output and "1 action(s)" in res.output


def test_replay_serves_recorded_and_flags_unseen(tmp_path: Path) -> None:
    rec = _recording(tmp_path)
    home = screenshot_hash("home")
    stdin = "\n".join(
        [
            json.dumps({"kind": "click", "target": "#buy", "screen": home}),
            json.dumps({"kind": "click", "target": "#buy", "screen": "unseen"}),
        ]
    )
    res = runner.invoke(app, ["cu", "replay", str(rec)], input=stdin)
    assert res.exit_code == 0, res.output
    lines = [ln for ln in res.stdout.splitlines() if ln.startswith("{")]
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["result"] == {"ok": True}
    assert "__flagged__" in second


def test_inspect_missing_file_fails() -> None:
    res = runner.invoke(app, ["cu", "inspect", "nope.json"])
    assert res.exit_code != 0
