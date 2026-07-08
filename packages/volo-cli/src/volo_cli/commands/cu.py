"""`volo cu` — inspect and replay computer-use recordings (M31).

* ``volo cu inspect <recording>`` — print the action-event trajectory.
* ``volo cu replay <recording>`` — read newline-delimited action events (JSON) from stdin and
  emit the recorded UI outcome for each; an unseen (action, screen) returns a flagged miss.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

cu_app = typer.Typer(
    name="cu",
    help="Record / replay computer-use (browser & desktop) agents at the action-event level.",
    no_args_is_help=True,
)

_CU_PREFIX = "cu."


@cu_app.command("inspect")
def cu_inspect(
    recording_path: Annotated[Path, typer.Argument(help="Path to a computer-use Recording JSON.")],
) -> None:
    """Print the action-event trajectory of a computer-use recording."""
    from volo_core import Recording

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    rec = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    n = 0
    for i, step in enumerate(rec.steps, start=1):
        p = step.payload
        if p.type != "tool_call" or not p.tool.startswith(_CU_PREFIX):
            continue
        n += 1
        kind = p.tool[len(_CU_PREFIX) :]
        target = p.request.get("target", "")
        value = p.request.get("value", "")
        screen = p.request.get("screen")
        extra = f" value={value!r}" if value else ""
        typer.echo(f"cu inspect: [{i:03d}] {kind:9} target={target!r}{extra} screen={screen}")
    typer.echo(f"cu inspect: {n} action(s) over {len(rec.steps)} step(s)")


@cu_app.command("replay")
def cu_replay(
    recording_path: Annotated[Path, typer.Argument(help="Path to a computer-use Recording JSON.")],
) -> None:
    """Serve recorded UI outcomes for action events read from stdin (JSON per line)."""
    import json

    from volo_computeruse import ActionEvent, ComputerUseReplayServer
    from volo_core import Recording

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    rec = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    server = ComputerUseReplayServer.from_recording(rec)
    typer.echo(
        f"cu replay: simulating {len(rec.steps)} recorded action(s) - one JSON action per line, "
        "Ctrl-D to stop",
        err=True,
    )
    served = flagged = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = ActionEvent.from_dict(json.loads(line))
        except (ValueError, json.JSONDecodeError) as exc:
            typer.echo(json.dumps({"__error__": str(exc)}))
            continue
        out = server.step(event)
        served += 1
        if "__flagged__" in out:
            flagged += 1
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    typer.echo(f"cu replay: {served} action(s), {flagged} flagged", err=True)
