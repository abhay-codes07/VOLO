"""`volo persona run|list|export` — driving a multi-turn agent against a persona."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app
from volo_personas import Persona, dump_persona

runner = CliRunner()

AGENT = "examples.clarifying_agent:run"


def test_run_with_builtin_persona_meets_goal(tmp_path: Path) -> None:
    report = tmp_path / "conv.json"
    res = runner.invoke(
        app,
        [
            "persona",
            "run",
            "--agent",
            AGENT,
            "--persona",
            "decisive-traveler",
            "--out",
            str(report),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "GOAL MET" in res.output
    assert "agent> What is your destination?" in res.output
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["goal_met"] is True and blob["turns"] == 3


def test_run_with_pack_and_require_goal_exit_6(tmp_path: Path) -> None:
    # a persona whose destination won't satisfy an expectation of Paris
    persona = Persona(
        name="mismatch",
        goal="go to Paris",
        facts={"destination": "Tokyo", "cabin": "economy", "one-way or round": "one-way"},
        expected=["Paris"],
    )
    pack = tmp_path / "p.json"
    dump_persona(persona, pack)

    res = runner.invoke(
        app,
        ["persona", "run", "--agent", AGENT, "--persona", str(pack), "--require-goal"],
    )
    assert res.exit_code == 6, res.output
    assert "GOAL NOT MET" in res.output


def test_unknown_persona_is_a_usage_error() -> None:
    res = runner.invoke(app, ["persona", "run", "--agent", AGENT, "--persona", "nope"])
    assert res.exit_code != 0
    assert "unknown persona" in res.output


def test_list_and_export(tmp_path: Path) -> None:
    listing = runner.invoke(app, ["persona", "list"])
    assert listing.exit_code == 0
    assert "decisive-traveler" in listing.output

    out = tmp_path / "exported.json"
    exp = runner.invoke(app, ["persona", "export", "decisive-traveler", str(out)])
    assert exp.exit_code == 0, exp.output
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["name"] == "decisive-traveler"
