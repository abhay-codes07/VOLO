"""`volo pack init|validate|install|list` — the pack lifecycle, end to end."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app

runner = CliRunner()


def test_init_validate_install_list(tmp_path: Path) -> None:
    pack = tmp_path / "attacks.json"
    store = tmp_path / "store"

    init = runner.invoke(
        app, ["pack", "init", "attacks", str(pack), "--name", "my-attacks", "--version", "1.2.0"]
    )
    assert init.exit_code == 0, init.output
    assert "my-attacks@1.2.0" in init.output
    blob = json.loads(pack.read_text(encoding="utf-8"))
    assert blob["manifest"]["kind"] == "attacks" and blob["manifest"]["n_items"] >= 50

    val = runner.invoke(app, ["pack", "validate", str(pack)])
    assert val.exit_code == 0, val.output
    assert "VALID" in val.output

    inst = runner.invoke(app, ["pack", "install", str(pack), "--dir", str(store)])
    assert inst.exit_code == 0, inst.output

    lst = runner.invoke(app, ["pack", "list", "--dir", str(store)])
    assert lst.exit_code == 0
    assert "my-attacks@1.2.0" in lst.output


def test_validate_rejects_tampered_pack(tmp_path: Path) -> None:
    pack = tmp_path / "personas.json"
    runner.invoke(app, ["pack", "init", "personas", str(pack)])
    blob = json.loads(pack.read_text(encoding="utf-8"))
    blob["items"].append({"name": "injected"})  # breaks the checksum
    pack.write_text(json.dumps(blob), encoding="utf-8")

    res = runner.invoke(app, ["pack", "validate", str(pack)])
    assert res.exit_code == 1
    assert "INVALID" in res.output and "checksum mismatch" in res.output


def test_init_unknown_kind_fails(tmp_path: Path) -> None:
    res = runner.invoke(app, ["pack", "init", "widgets", str(tmp_path / "x.json")])
    assert res.exit_code != 0


def test_install_duplicate_fails_without_force(tmp_path: Path) -> None:
    pack = tmp_path / "s.json"
    store = tmp_path / "store"
    runner.invoke(
        app, ["pack", "init", "scenarios", str(pack), "--name", "s", "--version", "1.0.0"]
    )
    assert runner.invoke(app, ["pack", "install", str(pack), "--dir", str(store)]).exit_code == 0
    dup = runner.invoke(app, ["pack", "install", str(pack), "--dir", str(store)])
    assert dup.exit_code == 1 and "already installed" in dup.output
