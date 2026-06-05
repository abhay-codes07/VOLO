"""`volo record` — capture a live agent run.

Currently a thin wrapper that imports a `<module>:<callable>` target, invokes it inside a
``Recorder`` context, and writes a Recording to disk. The auto-instrumentation of internal
model/tool calls is the next concrete task (see ``docs/STATUS.md``).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from volo_sdk import RecorderConfig, record


def _resolve(target: str) -> Callable[..., Any]:
    """Resolve a ``pkg.module:callable`` string to the callable.

    The CWD is prepended to ``sys.path`` so user-local modules (e.g. ``examples.echo_agent``)
    resolve even when ``volo`` is invoked as an installed script.
    """
    if ":" not in target:
        raise typer.BadParameter(f"Expected `module:callable`, got {target!r}")
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    module_path, attr = target.split(":", 1)
    mod = importlib.import_module(module_path)
    try:
        obj = getattr(mod, attr)
    except AttributeError as e:
        raise typer.BadParameter(f"{attr!r} not found in {module_path!r}") from e
    if not callable(obj):
        raise typer.BadParameter(f"{target!r} resolves to a non-callable: {type(obj).__name__}")
    return cast("Callable[..., Any]", obj)


def record_command(
    target: Annotated[
        str,
        typer.Argument(help="Agent entrypoint, e.g. examples.echo_agent:run."),
    ],
    input_: Annotated[
        str,
        typer.Option("--input", "-i", help="JSON-encoded input passed positionally to the agent."),
    ] = "{}",
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Where to write the Recording."),
    ] = None,
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="Base data dir for recordings + artifacts."),
    ] = Path(".volo"),
    framework: Annotated[
        str,
        typer.Option("--framework", help="Framework label for RunMeta."),
    ] = "raw",
    no_redact: Annotated[
        bool,
        typer.Option("--no-redact", help="Skip the redaction pass (NOT recommended)."),
    ] = False,
) -> None:
    """Wrap an agent entrypoint with the Volo Recorder and persist the run."""
    fn = _resolve(target)
    try:
        payload = json.loads(input_)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--input must be valid JSON: {e}") from e

    cfg = RecorderConfig(data_dir=data_dir, apply_redaction=not no_redact)
    with record(
        agent_name=target,
        framework=framework,
        config=cfg,
        out=out,
        save_on_exit=False,
    ) as rec:
        result = fn(payload) if payload != {} else fn()
        rec.set_final_output(result)
        path = rec.save(out)

    typer.echo(f"recording -> {path}")
