"""`volo migrate` — the migration lab, end to end."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from volo_cli.main import app
from volo_core import ModelCallPayload, Recording, ToolCallPayload

runner = CliRunner()


def _write(path: Path, answer: Any, model: str) -> None:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 3}))
    rec.add_step(
        ModelCallPayload(provider="p", model=model, request={"prompt": "s"}, response={"t": "y"})
    )
    rec.final_output = answer
    path.write_text(rec.to_json(), encoding="utf-8")


def test_clean_migration_recommends_exit_0(tmp_path: Path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write(a, {"hits": 3}, "claude-haiku-4-5")
    _write(b, {"hits": 3}, "llama3.2:3b")
    report = tmp_path / "report.json"

    res = runner.invoke(
        app,
        [
            "migrate",
            str(a),
            str(b),
            "--from",
            "claude-haiku-4-5",
            "--to",
            "llama3.2:3b",
            "--out",
            str(report),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "RECOMMEND" in res.output
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["recommendation"] == "recommend"
    assert blob["cost_b_usd"] == 0.0  # local model is free


def test_regression_blocks_exit_5(tmp_path: Path) -> None:
    base, cand = tmp_path / "base", tmp_path / "cand"
    base.mkdir()
    cand.mkdir()
    _write(base / "keep.json", {"hits": 3}, "m-a")
    _write(cand / "keep.json", {"hits": 3}, "m-b")
    _write(base / "break.json", {"hits": 3}, "m-a")
    _write(cand / "break.json", {"hits": 88888}, "m-b")  # ungrounded → regressed

    res = runner.invoke(app, ["migrate", str(base), str(cand)])
    assert res.exit_code == 5, res.output
    assert "BLOCK" in res.output
    assert "regressed" in res.output


def test_no_pairs_exits_2(tmp_path: Path) -> None:
    base, cand = tmp_path / "base", tmp_path / "cand"
    base.mkdir()
    cand.mkdir()
    _write(base / "x.json", {"a": 1}, "m-a")
    _write(cand / "y.json", {"a": 1}, "m-b")  # disjoint stems
    res = runner.invoke(app, ["migrate", str(base), str(cand)])
    assert res.exit_code == 2
    assert "no paired recordings" in res.output
