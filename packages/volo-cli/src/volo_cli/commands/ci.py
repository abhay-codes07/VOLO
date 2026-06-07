"""`volo ci` — GitHub-Action entrypoint. Same engine as ``run`` with CI-friendly output."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from volo_core import Recording


def ci_command(
    baseline: Annotated[Path, typer.Argument(help="Baseline Recording JSON file.")],
    agent: Annotated[
        str,
        typer.Option("--agent", help="Agent entrypoint, e.g. examples.calc_agent:run"),
    ] = ...,  # type: ignore[assignment]
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="JSON input passed to the agent."),
    ] = "{}",
    fail_under: Annotated[
        float,
        typer.Option("--fail-under", min=0.0, max=1.0, help="Verdict threshold."),
    ] = 0.9,
    n_runs: Annotated[int, typer.Option("--n", help="Repetitions per scenario.")] = 3,
    judge: Annotated[
        str,
        typer.Option("--judge", help="Faithfulness judge: heuristic | ollama | groq."),
    ] = "heuristic",
    max_cost_usd: Annotated[
        float | None,
        typer.Option("--max-cost-usd", help="Fail if this run's real API spend exceeds USD."),
    ] = None,
    summary_md: Annotated[
        Path | None,
        typer.Option(
            "--summary-md", help="Write a Markdown reliability summary (for PR comments)."
        ),
    ] = None,
    out: Annotated[
        Path,
        typer.Option("--out", help="Where to write the ReliabilityReport JSON."),
    ] = Path("./.volo/reports/latest.json"),
) -> None:
    """Run the full pipeline and exit non-zero on regression — designed for CI gating."""
    from volo_cli.commands._cost import cost_cap_breach, cost_lines
    from volo_cli.commands._judge import resolve_judge
    from volo_cli.commands._summary import report_markdown
    from volo_runner import OrchestratorConfig, orchestrate

    if not baseline.exists():
        raise typer.BadParameter(f"Baseline not found: {baseline}")
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input must be valid JSON: {e}") from e

    rec = Recording.from_json(baseline.read_text(encoding="utf-8"))
    report = orchestrate(
        rec,
        agent,
        config=OrchestratorConfig(
            n_runs=n_runs,
            fail_under=fail_under,
            agent_input=agent_input if agent_input != {} else None,
            judge=resolve_judge(judge),
        ),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.to_json() + "\n", encoding="utf-8")

    # Markdown summary: to a file (for a PR-comment step) and/or the GitHub job summary page.
    markdown = report_markdown(report)
    if summary_md is not None:
        summary_md.parent.mkdir(parents=True, exist_ok=True)
        summary_md.write_text(markdown, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(markdown)

    badge = "PASS" if report.verdict == "ship" else "FAIL"
    typer.echo("::group::Volo reliability")
    typer.echo(f"verdict = {badge} ({report.verdict})")
    for name, value in report.aggregate.items():
        bar = "#" * int(value * 20)
        typer.echo(f"  {name:<32} {value:.3f}  {bar}")
    for line in cost_lines(report):
        typer.echo(line)
    typer.echo(f"report -> {out}")
    typer.echo("::endgroup::")

    breach = cost_cap_breach(report, max_cost_usd)
    if breach is not None:
        typer.echo(breach, err=True)
        raise typer.Exit(2)

    raise typer.Exit(0 if report.verdict == "ship" else 1)
