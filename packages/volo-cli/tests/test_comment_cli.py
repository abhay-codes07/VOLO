"""`volo comment` — the sticky PR-comment renderer (M28)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from volo_cli.commands.comment import STICKY_MARKER, pr_comment_markdown
from volo_cli.main import app
from volo_compliance import build_evidence_pack
from volo_redteam import SafetyAnnex
from volo_reliability import ReliabilityReport

runner = CliRunner()


def _report(verdict: str = "ship") -> ReliabilityReport:
    return ReliabilityReport(
        baseline_run_id="run-1",
        aggregate={"trajectory_determinism": 1.0, "faithfulness": 0.5},
        verdict=verdict,  # type: ignore[arg-type]
        scenarios=[],
        fail_under=0.9,
    )


def test_markdown_has_sticky_marker_and_verdict() -> None:
    md = pr_comment_markdown(_report("ship"))
    assert md.startswith(STICKY_MARKER)
    assert "SHIP" in md
    assert "Trajectory determinism" in md and "`1.000`" in md


def test_markdown_folds_in_compliance() -> None:
    evidence = build_evidence_pack(
        agent_name="bot", frameworks=["soc2"], reliability=_report("ship")
    )
    md = pr_comment_markdown(_report("ship"), evidence)
    assert "Compliance evidence" in md
    assert "satisfied" in md and "soc2" in md


def test_comment_command_writes_and_prints(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(_report("no_ship").to_json(), encoding="utf-8")
    out = tmp_path / "comment.md"

    res = runner.invoke(app, ["comment", "--report", str(report), "--out", str(out)])
    assert res.exit_code == 0, res.output
    assert STICKY_MARKER in res.output
    body = out.read_text(encoding="utf-8")
    assert body.startswith(STICKY_MARKER) and "NO-SHIP" in body


def test_comment_command_with_evidence(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(_report("ship").to_json(), encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    pack = build_evidence_pack(
        agent_name="bot",
        frameworks=["eu_ai_act"],
        reliability=_report("ship"),
        safety=SafetyAnnex(
            baseline_run_id="r", verdict="safe", attacks_run=54, compromised=0, findings=[]
        ),
    )
    evidence.write_text(pack.to_json(), encoding="utf-8")

    res = runner.invoke(app, ["comment", "--report", str(report), "--evidence", str(evidence)])
    assert res.exit_code == 0, res.output
    assert "Compliance evidence" in res.output and "eu_ai_act" in res.output


def test_comment_command_missing_report_fails(tmp_path: Path) -> None:
    res = runner.invoke(app, ["comment", "--report", str(tmp_path / "nope.json")])
    assert res.exit_code != 0
