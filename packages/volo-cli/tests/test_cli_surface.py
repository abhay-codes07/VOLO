"""Smoke tests for the Typer surface: subcommands exist, `--help` works, exit codes are sane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from volo_cli.main import app

runner = CliRunner()


def test_root_help_lists_subcommands() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for sub in ("record", "sim", "run", "ci", "diff"):
        assert sub in res.stdout


def test_version_flag() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.stdout.strip()


@pytest.mark.parametrize("sub", ["record", "sim", "run", "ci", "diff"])
def test_each_subcommand_help(sub: str) -> None:
    res = runner.invoke(app, [sub, "--help"])
    assert res.exit_code == 0, res.stdout


def test_record_round_trips_a_recording(tmp_path: Path) -> None:
    """`volo record` should produce a valid Recording JSON on disk."""
    out = tmp_path / "rec.json"
    res = runner.invoke(
        app,
        [
            "record",
            "examples.echo_agent:run",
            "--input",
            '{"text": "hello"}',
            "--out",
            str(out),
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0, res.stdout
    assert out.exists()
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["recording_schema_version"] == "1.0.0"
    assert blob["final_output"] == {"echo": "HELLO"}
    # The proxy machinery from ADR-0004 should have auto-captured both calls.
    types = [s["payload"]["type"] for s in blob["steps"]]
    assert types == ["tool_call", "model_call"]


def test_sim_prints_transcript_for_valid_recording(tmp_path: Path) -> None:
    from volo_core import ModelCallPayload, Recording

    r = Recording()
    r.add_step(ModelCallPayload(provider="ollama", model="llama3.2:3b", request={"prompt": "x"}))
    path = tmp_path / "r.json"
    path.write_text(r.to_json(), encoding="utf-8")

    res = runner.invoke(app, ["sim", str(path)])
    assert res.exit_code == 0
    assert "loaded 1 step" in res.stdout
    assert "model_call" in res.stdout


def test_diff_command_runs_and_reports(tmp_path: Path) -> None:
    """`volo diff` prints a human-readable diff and exits 0 when identical."""
    from volo_core import ModelCallPayload, Recording

    r = Recording()
    r.add_step(ModelCallPayload(provider="x", model="y", request={"p": 1}, response={"t": "o"}))
    base = tmp_path / "base.json"
    cand = tmp_path / "cand.json"
    base.write_text(r.to_json(), encoding="utf-8")
    cand.write_text(r.to_json(), encoding="utf-8")

    res = runner.invoke(app, ["diff", str(base), str(cand)])
    assert res.exit_code == 0, res.stdout
    assert "no trajectory divergence" in res.stdout


def test_run_command_executes_and_returns_verdict(tmp_path: Path) -> None:
    """`volo run` should orchestrate and exit 0 (ship) or 1 (no_ship)."""
    # First record a baseline against the calc_agent.
    from examples.calc_agent import run as calc

    from volo_core import current_recorder
    from volo_sdk import Recorder, RecorderConfig

    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        rec.set_final_output(calc({"a": 2, "b": 3, "c": 4}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(rec.recording.to_json(), encoding="utf-8")

    report_out = tmp_path / "report.json"
    res = runner.invoke(
        app,
        [
            "run",
            str(baseline),
            "--agent",
            "examples.calc_agent:run",
            "--input",
            '{"a":2,"b":3,"c":4}',
            "--n",
            "2",
            "--out",
            str(report_out),
        ],
    )
    assert res.exit_code in (0, 1), res.stdout
    assert "verdict:" in res.stdout
    assert "cost:" in res.stdout  # cost summary is surfaced (bible §11)
    assert report_out.exists()
    blob = json.loads(report_out.read_text(encoding="utf-8"))
    assert "scenarios" in blob and len(blob["scenarios"]) == 7
    assert "recorded_cost_usd" in blob and "simulated_cost_usd" in blob
