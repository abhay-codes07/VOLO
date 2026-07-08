"""`volo multiagent run` — test an orchestrator against simulated sub-agents (M32).

Drives an orchestrator (a crew/graph/router) against counterparties defined as personas, and
reports the system interaction: which sub-agents were reached, any delegations to unknown agents,
and a system verdict. Exits 9 when the system is broken (unknown agent, error, or unmet goal).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

BROKEN_EXIT_CODE = 9

multiagent_app = typer.Typer(
    name="multiagent",
    help="Test multi-agent orchestrators by simulating their sub-agents as counterparties.",
    no_args_is_help=True,
)


@multiagent_app.command("run")
def multiagent_run(
    agent: Annotated[
        str, typer.Option("--orchestrator", "--agent", help="Orchestrator, as `module:callable`.")
    ],
    counterparties: Annotated[
        Path, typer.Option("--counterparties", help="JSON of {name: persona} sub-agents.")
    ],
    recording: Annotated[
        Path | None,
        typer.Option("--recording", help="Recording for the orchestrator's non-delegation tools."),
    ] = None,
    input_: Annotated[
        str, typer.Option("--input", "-i", help="JSON input passed to the orchestrator.")
    ] = "{}",
    expect: Annotated[
        list[str] | None,
        typer.Option("--expect", help="Substring the final output must contain (repeatable)."),
    ] = None,
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the system report JSON here.")
    ] = None,
) -> None:
    """Run the orchestrator against simulated sub-agents; exit 9 if the system is broken."""
    import json

    from volo_core import Recording
    from volo_multiagent import load_counterparties_json, run_multiagent
    from volo_runner import resolve_agent

    if not counterparties.exists():
        raise typer.BadParameter(f"Counterparties file not found: {counterparties}")
    cps = load_counterparties_json(counterparties.read_text(encoding="utf-8"))
    rec = (
        Recording.from_json(recording.read_text(encoding="utf-8"))
        if recording is not None and recording.exists()
        else None
    )
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--input must be valid JSON: {exc}") from exc

    report = run_multiagent(
        resolve_agent(agent),
        cps,
        recording=rec,
        agent_input=agent_input if agent_input != {} else None,
        expected=list(expect) if expect else None,
    )

    typer.echo(f"multiagent: orchestrator {report.orchestrator} -> {report.verdict.upper()}")
    for m in report.messages:
        marker = "!!" if m.unknown else "->"
        reply = "(unknown agent)" if m.unknown else f"{(m.reply or '')[:60]!r}"
        typer.echo(f"multiagent: {marker} {m.to:14} {m.message[:40]!r} => {reply}")
    if report.unreached:
        typer.echo(f"multiagent: unreached sub-agent(s): {', '.join(report.unreached)}")
    if report.unknown_agents:
        typer.echo(f"multiagent: unknown agent(s): {', '.join(report.unknown_agents)}")
    if report.error:
        typer.echo(f"multiagent: orchestrator errored - {report.error}")
    typer.echo(
        f"multiagent: {report.delegations} delegation(s), goal_met={report.goal_met} -> "
        f"{report.verdict.upper()}"
    )

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json() + "\n", encoding="utf-8")
        typer.echo(f"multiagent: report -> {out}")

    if report.verdict == "broken":
        raise typer.Exit(BROKEN_EXIT_CODE)
