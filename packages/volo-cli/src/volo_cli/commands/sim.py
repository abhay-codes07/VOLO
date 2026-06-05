"""`volo sim` — boot a SimulatedEnvironment from a recording.

Two modes:

* ``volo sim <recording.json>`` — print the trajectory transcript.
* ``volo sim <recording.json> --agent <module:callable>`` — additionally drive the agent
  under a Tier-1 replayer of the recording. Useful for "does my code still behave the same way
  given the recorded environment?" — a cheap, deterministic smoke test.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from volo_core import Recording, current_environment
from volo_simulator import ReplayMiss, Tier1Replayer


def sim_command(
    recording_path: Annotated[Path, typer.Argument(help="Path to a Recording JSON file.")],
    agent: Annotated[
        str | None,
        typer.Option("--agent", help="Drive `module:callable` through the Tier-1 replayer."),
    ] = None,
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="JSON input for the agent (only used with --agent)."),
    ] = "{}",
    transcript: Annotated[
        bool,
        typer.Option("--transcript/--no-transcript", help="Print the trajectory."),
    ] = True,
) -> None:
    """Load a Recording and either print its transcript or replay it through an agent."""
    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")

    rec = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    typer.echo(f"loaded {len(rec.steps)} step(s) from {recording_path}")

    if transcript:
        for i, step in enumerate(rec.steps, start=1):
            typer.echo(f"  [{i:03d}] {step.type:10} {_brief(step.payload)}")

    if agent is None:
        return

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    mod_path, _, attr = agent.partition(":")
    if not attr:
        raise typer.BadParameter(f"Expected `module:callable`, got {agent!r}")
    fn = getattr(importlib.import_module(mod_path), attr)
    try:
        payload = json.loads(input_)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input must be valid JSON: {e}") from e

    env = Tier1Replayer.from_recording(rec)
    typer.echo(f"sim: Tier-1 replayer stats = {env.stats()}")
    with current_environment(env):
        try:
            result = fn(payload) if payload != {} else fn()
        except ReplayMiss as e:
            typer.echo(f"sim: REPLAY MISS — {e}")
            raise typer.Exit(3) from e
    typer.echo(f"sim: agent returned {json.dumps(result, default=str)}")


def _brief(payload: Any) -> str:
    if payload.type == "model_call":
        return f"{payload.provider}/{payload.model}"
    if payload.type == "tool_call":
        return str(payload.tool)
    return str(payload.label)
