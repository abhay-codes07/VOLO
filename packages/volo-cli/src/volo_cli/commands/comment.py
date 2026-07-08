"""`volo comment` — render a sticky PR comment from a reliability report (+ optional compliance).

The GitHub PR-check Action runs ``volo ci`` (→ report.json), optionally ``volo compliance build``
(→ evidence.json), then this command to produce one Markdown comment body. A hidden marker at the
top lets the Action find and *update* its previous comment instead of spamming a new one on every
push. Pure formatting — no network — so it's trivially testable and needs no hosting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from volo_cli.commands._summary import report_markdown

STICKY_MARKER = "<!-- volo-pr-check -->"
_STATE_EMOJI = {"satisfied": "✅", "partial": "⚠️", "unmet": "❌"}


def pr_comment_markdown(report: Any, evidence: Any = None) -> str:
    """Combine the reliability summary and (optional) compliance summary into one sticky comment."""
    parts: list[str] = [STICKY_MARKER, "", report_markdown(report).rstrip()]
    if evidence is not None:
        c = evidence.counts()
        parts += [
            "",
            "## 📋 Compliance evidence",
            "",
            f"Frameworks: {', '.join(evidence.frameworks)} — "
            f"**{c['satisfied']} satisfied · {c['partial']} partial · {c['unmet']} unmet** "
            "<sub>(mapping aid, not legal advice)</sub>",
            "",
            "| Framework | Control | Status |",
            "|---|---|---|",
        ]
        for ctl in evidence.controls:
            emoji = _STATE_EMOJI.get(ctl.state, "")
            parts.append(f"| {ctl.framework} | `{ctl.control_id}` | {emoji} {ctl.state} |")
    return "\n".join(parts) + "\n"


def comment_command(
    report: Annotated[
        Path, typer.Option("--report", help="ReliabilityReport JSON (from volo ci).")
    ],
    evidence: Annotated[
        Path | None,
        typer.Option("--evidence", help="EvidencePack JSON (from volo compliance build)."),
    ] = None,
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the comment Markdown here.")
    ] = None,
) -> None:
    """Render a sticky PR-comment Markdown (reliability + optional compliance) to stdout / --out."""
    from volo_reliability import ReliabilityReport

    if not report.exists():
        raise typer.BadParameter(f"Report not found: {report}")
    rel = ReliabilityReport.from_json(report.read_text(encoding="utf-8"))

    ev = None
    if evidence is not None:
        if not evidence.exists():
            raise typer.BadParameter(f"Evidence pack not found: {evidence}")
        from volo_compliance import EvidencePack

        ev = EvidencePack.model_validate_json(evidence.read_text(encoding="utf-8"))

    markdown = pr_comment_markdown(rel, ev)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
    # Emit as UTF-8 bytes: the comment body carries emoji, and stdout may be a cp1252 console
    # (Windows). Bytes bypass the console text encoder so piping to a file / the Action is safe.
    typer.echo(markdown.encode("utf-8"))
