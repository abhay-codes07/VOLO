"""`volo horizon` — the long-horizon drift rig (M18).

Replays a task for N episodes with the agent's memory threaded forward, and reports how the
reliability surface decays across episodes. Exits 7 when the agent degrades (context rot, memory
drift, accumulation) — distinct from reliability 1, drift 3, redteam 4, migrate 5, persona 6.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

DEGRADES_EXIT_CODE = 7
_SPARK_RAMP = " .:-=+*#@"  # ASCII on purpose (Windows consoles mangle unicode blocks)


def horizon_command(
    recording_path: Annotated[Path, typer.Argument(help="Baseline Recording JSON (tool replay).")],
    agent: Annotated[str, typer.Option("--agent", help="Agent under test, as `module:callable`.")],
    episodes: Annotated[int, typer.Option("--episodes", "-n", help="Number of episodes.")] = 10,
    input_: Annotated[
        str, typer.Option("--input", "-i", help="JSON base input merged into every episode.")
    ] = "{}",
    judge: Annotated[
        str, typer.Option("--judge", help="Faithfulness judge: heuristic | ollama | groq.")
    ] = "heuristic",
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the long-horizon report JSON here.")
    ] = None,
) -> None:
    """Run the agent for N episodes carrying memory forward; exit 7 if it degrades."""
    import json

    from volo_cli.commands._judge import resolve_judge
    from volo_core import Recording
    from volo_longhorizon import run_long_horizon
    from volo_runner import resolve_agent

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    baseline = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    try:
        base_input = json.loads(input_)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--input must be valid JSON: {exc}") from exc

    report = run_long_horizon(
        baseline,
        resolve_agent(agent),
        episodes=episodes,
        base_input=base_input if base_input != {} else None,
        judge=resolve_judge(judge),
        agent_name=agent,
    )

    faiths = [r.faithfulness for r in report.results]
    spark = "".join(
        _SPARK_RAMP[round(max(0.0, min(1.0, f)) * (len(_SPARK_RAMP) - 1))] for f in faiths
    )
    typer.echo(f"horizon: {agent} over {report.episodes} episode(s)")
    typer.echo(
        f"horizon: faithfulness [{spark}] {report.faithfulness_start:.2f} -> {report.faithfulness_end:.2f}"
    )
    typer.echo(
        f"horizon: stability {report.stability:.2f}  "
        f"output-consistency {report.output_consistency:.2f}  "
        f"slope {report.faithfulness_slope:+.4f}"
    )
    if report.first_degraded_episode is not None:
        typer.echo(f"horizon: first degraded at episode {report.first_degraded_episode}")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json() + "\n", encoding="utf-8")
        typer.echo(f"horizon: report -> {out}")

    typer.echo(f"horizon: verdict -> {report.verdict.upper()}")
    if report.verdict == "degrades":
        raise typer.Exit(DEGRADES_EXIT_CODE)
