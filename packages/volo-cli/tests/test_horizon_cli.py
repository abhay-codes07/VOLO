"""`volo horizon` — the long-horizon drift rig, end to end."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app
from volo_core import Recording, ToolCallPayload

runner = CliRunner()


def _baseline(tmp_path: Path) -> Path:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    path = tmp_path / "baseline.json"
    path.write_text(rec.to_json(), encoding="utf-8")
    return path


def test_stable_agent_exit_0(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        [
            "horizon",
            str(_baseline(tmp_path)),
            "--agent",
            "examples.drifting_agent:stable",
            "-n",
            "6",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "STABLE" in res.output


def test_drifting_agent_exit_7(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    res = runner.invoke(
        app,
        [
            "horizon",
            str(_baseline(tmp_path)),
            "--agent",
            "examples.drifting_agent:drifting",
            "-n",
            "8",
            "--out",
            str(report),
        ],
    )
    assert res.exit_code == 7, res.output
    assert "DEGRADES" in res.output
    assert "first degraded at episode 3" in res.output
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["verdict"] == "degrades" and blob["first_degraded_episode"] == 3
    assert len(blob["results"]) == 8


def test_missing_recording_fails(tmp_path: Path) -> None:
    res = runner.invoke(
        app, ["horizon", str(tmp_path / "nope.json"), "--agent", "examples.drifting_agent:stable"]
    )
    assert res.exit_code != 0
