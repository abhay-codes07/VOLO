"""`volo compliance build|verify` — evidence pack lifecycle end to end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from volo_cli.main import app
from volo_redteam import SafetyAnnex
from volo_reliability import ReliabilityReport

runner = CliRunner()


def _artifacts(tmp_path: Path, *, ship: bool = True, safe: bool = True) -> tuple[Path, Path, Path]:
    rel = tmp_path / "report.json"
    rel.write_text(
        ReliabilityReport(
            baseline_run_id="r1",
            aggregate={"faithfulness": 1.0},
            verdict="ship" if ship else "no_ship",
            scenarios=[],
        ).model_dump_json(),
        encoding="utf-8",
    )
    ann = tmp_path / "annex.json"
    ann.write_text(
        SafetyAnnex(
            baseline_run_id="r1",
            verdict="safe" if safe else "vulnerable",
            attacks_run=54,
            compromised=0 if safe else 3,
            findings=[],
        ).model_dump_json(),
        encoding="utf-8",
    )
    dft = tmp_path / "drift.json"
    dft.write_text(json.dumps({"drifted": False, "findings": []}), encoding="utf-8")
    return rel, ann, dft


def test_build_full_evidence_all_satisfied(tmp_path: Path) -> None:
    rel, ann, dft = _artifacts(tmp_path)
    out = tmp_path / "evidence.json"
    md = tmp_path / "evidence.md"
    res = runner.invoke(
        app,
        [
            "compliance",
            "build",
            "--agent",
            "bot",
            "--reliability",
            str(rel),
            "--safety",
            str(ann),
            "--drift",
            str(dft),
            "--out",
            str(out),
            "--md",
            str(md),
            "--require-satisfied",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "0 unmet" in res.output
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["checksum"] and all(c["state"] == "satisfied" for c in blob["controls"])
    assert md.read_text(encoding="utf-8").startswith("# Compliance evidence")


def test_require_satisfied_exits_8_when_unmet(tmp_path: Path) -> None:
    rel, _, _ = _artifacts(tmp_path)
    # only reliability → monitoring/security controls unmet
    res = runner.invoke(
        app,
        [
            "compliance",
            "build",
            "--agent",
            "bot",
            "--reliability",
            str(rel),
            "--out",
            str(tmp_path / "e.json"),
            "--require-satisfied",
        ],
    )
    assert res.exit_code == 8
    assert "unmet" in res.output


def test_sign_then_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rel, ann, dft = _artifacts(tmp_path)
    out = tmp_path / "evidence.json"
    keyring = tmp_path / "keyring.json"
    keyring.write_text(json.dumps({"auditor": "s3cret"}), encoding="utf-8")

    monkeypatch.setenv("VOLO_PACK_SECRET", "s3cret")
    build = runner.invoke(
        app,
        [
            "compliance",
            "build",
            "--agent",
            "bot",
            "--reliability",
            str(rel),
            "--safety",
            str(ann),
            "--drift",
            str(dft),
            "--out",
            str(out),
            "--sign",
            "auditor",
        ],
    )
    assert build.exit_code == 0, build.output
    assert "signed by 'auditor'" in build.output

    ver = runner.invoke(app, ["compliance", "verify", str(out), "--keyring", str(keyring)])
    assert ver.exit_code == 0
    assert "checksum OK" in ver.output and "VALID" in ver.output


def test_verify_detects_tampering(tmp_path: Path) -> None:
    rel, _, _ = _artifacts(tmp_path)
    out = tmp_path / "evidence.json"
    runner.invoke(
        app, ["compliance", "build", "--agent", "bot", "--reliability", str(rel), "--out", str(out)]
    )
    blob = json.loads(out.read_text(encoding="utf-8"))
    blob["agent_name"] = "evil-bot"  # checksum no longer matches
    out.write_text(json.dumps(blob), encoding="utf-8")

    res = runner.invoke(app, ["compliance", "verify", str(out)])
    assert res.exit_code == 1 and "CHECKSUM MISMATCH" in res.output


def test_build_requires_at_least_one_artifact(tmp_path: Path) -> None:
    res = runner.invoke(
        app, ["compliance", "build", "--agent", "bot", "--out", str(tmp_path / "e.json")]
    )
    assert res.exit_code != 0
