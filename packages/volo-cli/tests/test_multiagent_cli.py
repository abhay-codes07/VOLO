"""`volo multiagent run` — orchestrator system test end to end."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app

runner = CliRunner()

ORCH = "examples.orchestrator_agent:run"


def _counterparties(tmp_path: Path, *, include_writer: bool = True) -> Path:
    data = {
        "researcher": {"facts": {"research": "three cited sources"}},
    }
    if include_writer:
        data["writer"] = {"facts": {"write": "a polished draft"}}
    path = tmp_path / "cps.json"
    path.write_text(json.dumps({"counterparties": data}), encoding="utf-8")
    return path


def test_healthy_system_exit_0(tmp_path: Path) -> None:
    report = tmp_path / "sys.json"
    res = runner.invoke(
        app,
        [
            "multiagent",
            "run",
            "--orchestrator",
            ORCH,
            "--counterparties",
            str(_counterparties(tmp_path)),
            "--input",
            '{"topic": "volo"}',
            "--out",
            str(report),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "HEALTHY" in res.output
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["reached"] == ["researcher", "writer"] and blob["delegations"] == 2


def test_unknown_agent_breaks_exit_9(tmp_path: Path) -> None:
    # omit 'writer' → the orchestrator delegates to an unknown agent
    res = runner.invoke(
        app,
        [
            "multiagent",
            "run",
            "--orchestrator",
            ORCH,
            "--counterparties",
            str(_counterparties(tmp_path, include_writer=False)),
        ],
    )
    assert res.exit_code == 9, res.output
    assert "BROKEN" in res.output and "writer" in res.output


def test_expect_marker_gates(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        [
            "multiagent",
            "run",
            "--orchestrator",
            ORCH,
            "--counterparties",
            str(_counterparties(tmp_path)),
            "--expect",
            "NOPE",
        ],
    )
    assert res.exit_code == 9
    assert "goal_met=False" in res.output


def test_missing_counterparties_fails(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        [
            "multiagent",
            "run",
            "--orchestrator",
            ORCH,
            "--counterparties",
            str(tmp_path / "no.json"),
        ],
    )
    assert res.exit_code != 0
