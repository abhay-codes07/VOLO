"""`volo certify run|verify|badge` — the certification lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from volo_cli.main import app
from volo_core import Recording, ToolCallPayload

runner = CliRunner()


def _recording(tmp_path: Path) -> Path:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    path = tmp_path / "rec.json"
    path.write_text(rec.to_json(), encoding="utf-8")
    return path


def test_certify_guarded_agent_signed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rec = _recording(tmp_path)
    cert = tmp_path / "cert.json"
    badge = tmp_path / "badge.svg"
    keyring = tmp_path / "k.json"
    keyring.write_text(json.dumps({"volo-official": "s3cret"}), encoding="utf-8")
    monkeypatch.setenv("VOLO_PACK_SECRET", "s3cret")

    res = runner.invoke(
        app,
        [
            "certify",
            "run",
            str(rec),
            "--agent",
            "examples.vulnerable_agent:guarded_summarizer",
            "--out",
            str(cert),
            "--badge",
            str(badge),
            "--sign",
            "volo-official",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "CERTIFIED" in res.output
    assert badge.read_text(encoding="utf-8").startswith("<svg")

    ver = runner.invoke(app, ["certify", "verify", str(cert), "--keyring", str(keyring)])
    assert ver.exit_code == 0 and "VALID" in ver.output and "checksum OK" in ver.output


def test_certify_vulnerable_agent_exit_10(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        [
            "certify",
            "run",
            str(_recording(tmp_path)),
            "--agent",
            "examples.vulnerable_agent:naive_summarizer",
        ],
    )
    assert res.exit_code == 10, res.output
    assert "NOT CERTIFIED" in res.output and "not safe" in res.output


def test_certify_verify_detects_tampering(tmp_path: Path) -> None:
    rec = _recording(tmp_path)
    cert = tmp_path / "cert.json"
    runner.invoke(
        app,
        [
            "certify",
            "run",
            str(rec),
            "--agent",
            "examples.vulnerable_agent:guarded_summarizer",
            "--out",
            str(cert),
        ],
    )
    blob = json.loads(cert.read_text(encoding="utf-8"))
    blob["volo_score"] = 100  # tamper
    cert.write_text(json.dumps(blob), encoding="utf-8")
    res = runner.invoke(app, ["certify", "verify", str(cert)])
    assert res.exit_code == 1 and "CHECKSUM MISMATCH" in res.output


def test_certify_badge_command(tmp_path: Path) -> None:
    rec = _recording(tmp_path)
    cert = tmp_path / "cert.json"
    runner.invoke(
        app,
        [
            "certify",
            "run",
            str(rec),
            "--agent",
            "examples.vulnerable_agent:guarded_summarizer",
            "--out",
            str(cert),
        ],
    )
    badge = tmp_path / "b.svg"
    res = runner.invoke(app, ["certify", "badge", str(cert), str(badge)])
    assert res.exit_code == 0 and badge.exists()
    assert "PASS" in res.output
