"""`volo run` — orchestrate scenarios + reliability over a baseline recording."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from volo_core import Recording


def run_command(
    recording_path: Annotated[Path, typer.Argument(help="Baseline Recording.")],
    agent: Annotated[
        str,
        typer.Option("--agent", help="Agent entrypoint, e.g. examples.calc_agent:run"),
    ] = ...,  # type: ignore[assignment]
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="JSON input passed to the agent."),
    ] = "{}",
    n_runs: Annotated[
        int,
        typer.Option("--n", help="Repetitions per scenario."),
    ] = 3,
    seed: Annotated[int, typer.Option("--seed", help="RNG seed.")] = 0,
    fail_under: Annotated[
        float,
        typer.Option("--fail-under", help="Verdict threshold per aggregate metric."),
    ] = 0.9,
    judge: Annotated[
        str,
        typer.Option("--judge", help="Faithfulness judge: heuristic | ollama | groq."),
    ] = "heuristic",
    max_cost_usd: Annotated[
        float | None,
        typer.Option("--max-cost-usd", help="Fail if this run's real API spend exceeds USD."),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Where to write the ReliabilityReport JSON."),
    ] = None,
) -> None:
    """Execute scenarios against the agent under a Tier-1 replayer; emit a ReliabilityReport."""
    from volo_cli.commands._cost import cost_cap_breach, cost_lines
    from volo_cli.commands._judge import resolve_judge
    from volo_runner import OrchestratorConfig, orchestrate

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input must be valid JSON: {e}") from e

    baseline = Recording.from_json(recording_path.read_text(encoding="utf-8"))

    report = orchestrate(
        baseline,
        agent,
        config=OrchestratorConfig(
            n_runs=n_runs,
            seed=seed,
            fail_under=fail_under,
            agent_input=agent_input if agent_input != {} else None,
            judge=resolve_judge(judge),
        ),
    )

    blob = report.to_json()
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(blob + "\n", encoding="utf-8")
        typer.echo(f"report -> {out}")

    typer.echo(f"verdict: {report.verdict.upper()}")
    for name, value in report.aggregate.items():
        typer.echo(f"  {name:<32} {value:.3f}")
    for line in cost_lines(report):
        typer.echo(line)

    breach = cost_cap_breach(report, max_cost_usd)
    if breach is not None:
        typer.echo(breach, err=True)
        raise typer.Exit(2)

    raise typer.Exit(0 if report.verdict == "ship" else 1)
