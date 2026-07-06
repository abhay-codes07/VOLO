"""`volo persona` — drive an agent against a simulated user/counterparty (M17).

* ``volo persona run --agent m:fn --persona p.json`` — run a multi-turn agent against a persona;
  print the conversation and whether the agent met the persona's goal.
* ``volo persona list`` — show the built-in personas.
* ``volo persona export <persona> out.json`` — write a built-in persona as an editable pack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

GOAL_NOT_MET_EXIT_CODE = 6

persona_app = typer.Typer(
    name="persona",
    help="Simulated users & counterparties — drive multi-turn agents deterministically.",
    no_args_is_help=True,
)


@persona_app.command("run")
def persona_run(
    agent: Annotated[str, typer.Option("--agent", help="Agent under test, as `module:callable`.")],
    persona: Annotated[
        str,
        typer.Option("--persona", help="Persona pack JSON, or a built-in persona name."),
    ],
    recording: Annotated[
        Path | None,
        typer.Option("--recording", help="Recording for the agent's non-user tools (optional)."),
    ] = None,
    input_: Annotated[
        str, typer.Option("--input", "-i", help="JSON input passed to the agent.")
    ] = "{}",
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the conversation report JSON here.")
    ] = None,
    require_goal: Annotated[
        bool,
        typer.Option("--require-goal", help="Exit 6 if the agent does not meet the persona goal."),
    ] = False,
) -> None:
    """Drive the agent against the persona and print the conversation + goal verdict."""
    import json

    from volo_core import Recording
    from volo_personas import default_personas, drive_persona, load_persona
    from volo_runner import resolve_agent

    persona_path = Path(persona)
    if persona_path.exists():
        p = load_persona(persona_path)
    else:
        match = next((x for x in default_personas() if x.name == persona), None)
        if match is None:
            names = ", ".join(x.name for x in default_personas())
            raise typer.BadParameter(f"unknown persona {persona!r}. Built-in: {names}")
        p = match

    rec = (
        Recording.from_json(recording.read_text(encoding="utf-8"))
        if recording is not None and recording.exists()
        else None
    )
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--input must be valid JSON: {exc}") from exc

    report = drive_persona(
        resolve_agent(agent),
        p,
        recording=rec,
        agent_input=agent_input if agent_input != {} else None,
    )

    typer.echo(f"persona: {report.persona} - goal: {report.goal or '(none)'}")
    for i, turn in enumerate(report.transcript, start=1):
        typer.echo(f"persona:  [{i}] agent> {turn['question']}")
        typer.echo(f"persona:      user> {turn['answer']}")
    if report.error:
        typer.echo(f"persona: agent errored - {report.error}")
    typer.echo(f"persona: final -> {json.dumps(report.final_output, default=str)}")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json() + "\n", encoding="utf-8")
        typer.echo(f"persona: report -> {out}")

    verdict = "GOAL MET" if report.goal_met else "GOAL NOT MET"
    typer.echo(f"persona: {report.turns} turn(s) -> {verdict}")
    if require_goal and not report.goal_met:
        raise typer.Exit(GOAL_NOT_MET_EXIT_CODE)


@persona_app.command("list")
def persona_list() -> None:
    """List the built-in personas."""
    from volo_personas import default_personas

    personas = default_personas()
    for p in personas:
        typer.echo(f"persona: {p.name:20} facts={len(p.facts)} script={len(p.script)} - {p.goal}")
    typer.echo(f"persona: {len(personas)} built-in persona(s)")


@persona_app.command("export")
def persona_export(
    name: Annotated[str, typer.Argument(help="Built-in persona name to export.")],
    out: Annotated[Path, typer.Argument(help="Where to write the persona pack JSON.")],
) -> None:
    """Export a built-in persona as an editable pack."""
    from volo_personas import default_personas, dump_persona

    p = next((x for x in default_personas() if x.name == name), None)
    if p is None:
        names = ", ".join(x.name for x in default_personas())
        raise typer.BadParameter(f"unknown persona {name!r}. Built-in: {names}")
    path = dump_persona(p, out)
    typer.echo(f"persona: exported {name!r} -> {path}")
