"""`volo init` — 60-second quickstart: wrap an agent, record a run, score its reliability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from volo_core import Recording


def init_command(
    target: Annotated[
        str,
        typer.Argument(help="Agent entrypoint, e.g. examples.calc_agent:run."),
    ],
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="JSON input passed to the agent."),
    ] = "{}",
    name: Annotated[
        str,
        typer.Option("--name", help="Name for the recording/report files."),
    ] = "baseline",
    n_runs: Annotated[
        int,
        typer.Option("--n", help="Repetitions per scenario."),
    ] = 2,
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="Base data dir for recordings + reports."),
    ] = Path(".volo"),
) -> None:
    """Record an agent once and score it — the fastest way to try Volo end-to-end."""
    from volo_cli.commands._cost import cost_lines
    from volo_cli.commands.record import _resolve
    from volo_runner import OrchestratorConfig, orchestrate
    from volo_sdk import RecorderConfig, record

    try:
        payload = json.loads(input_)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input must be valid JSON: {e}") from e

    fn = _resolve(target)
    agent_input = payload if payload != {} else None

    # 1) Record one real run.
    typer.echo("[1/3] recording a baseline run...")
    rec_path = data_dir / "recordings" / f"{name}.json"
    cfg = RecorderConfig(data_dir=data_dir, apply_redaction=True)
    with record(
        agent_name=target, framework="raw", config=cfg, out=rec_path, save_on_exit=False
    ) as rec:
        result = fn(payload) if agent_input is not None else fn()
        rec.set_final_output(result)
        rec.save(rec_path)
    typer.echo(f"   captured {len(rec.recording.steps)} step(s) -> {rec_path}")

    # 2) Replay against adversarial scenarios -- deterministic, no live calls.
    typer.echo("[2/3] replaying against adversarial scenarios (deterministic, $0)...")
    baseline = Recording.from_json(rec_path.read_text(encoding="utf-8"))
    report = orchestrate(
        baseline,
        target,
        config=OrchestratorConfig(n_runs=n_runs, agent_input=agent_input),
    )
    report_path = data_dir / "reports" / f"{name}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_json() + "\n", encoding="utf-8")

    # 3) Verdict.
    typer.echo("")
    typer.echo(f"[3/3] verdict: {report.verdict.upper()}  ({len(report.scenarios)} scenarios)")
    for metric, value in report.aggregate.items():
        typer.echo(f"  {metric:<32} {value:.3f}")
    for line in cost_lines(report):
        typer.echo(line)

    # Next steps.
    typer.echo("")
    typer.echo("next steps:")
    typer.echo(f"  - inspect the run:  uv run volo sim {rec_path}")
    typer.echo(f"  - full report JSON: {report_path}")
    typer.echo(
        "  - gate it in CI:    copy .github/workflows/volo-pr-reliability.yml into your repo"
    )
    typer.echo("  - smarter judge:    put GROQ_API_KEY in .env, then add --judge groq")
