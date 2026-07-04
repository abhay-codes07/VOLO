"""`volo redteam run|list|export` — the safety gate, end to end."""

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


def test_run_flags_vulnerable_agent_exit_4(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    annex = tmp_path / "annex.json"
    res = runner.invoke(
        app,
        [
            "redteam",
            "run",
            str(baseline),
            "--agent",
            "examples.vulnerable_agent:naive_summarizer",
            "--out",
            str(annex),
        ],
    )
    assert res.exit_code == 4, res.output
    assert "VULNERABLE" in res.output
    assert "COMPROMISED" in res.output
    blob = json.loads(annex.read_text(encoding="utf-8"))
    assert blob["verdict"] == "vulnerable" and blob["compromised"] >= 50


def test_run_clears_guarded_agent_exit_0(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    res = runner.invoke(
        app,
        [
            "redteam",
            "run",
            str(baseline),
            "--agent",
            "examples.vulnerable_agent:guarded_summarizer",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "SAFE" in res.output


def test_list_shows_corpus_by_class() -> None:
    res = runner.invoke(app, ["redteam", "list"])
    assert res.exit_code == 0
    assert "prompt_injection" in res.output
    assert "class(es)" in res.output


def test_export_then_run_with_pack(tmp_path: Path) -> None:
    pack = tmp_path / "pack.json"
    exp = runner.invoke(app, ["redteam", "export", str(pack)])
    assert exp.exit_code == 0, exp.output
    assert pack.exists()

    baseline = _baseline(tmp_path)
    res = runner.invoke(
        app,
        [
            "redteam",
            "run",
            str(baseline),
            "--agent",
            "examples.vulnerable_agent:guarded_summarizer",
            "--pack",
            str(pack),
        ],
    )
    assert res.exit_code == 0, res.output
