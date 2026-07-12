"""Top-level `volo` Typer app. Wires the five subcommands from bible §9.5."""

from __future__ import annotations

import contextlib
import sys

import typer

from volo_cli.commands.certify import certify_app
from volo_cli.commands.ci import ci_command
from volo_cli.commands.comment import comment_command
from volo_cli.commands.compliance import compliance_app
from volo_cli.commands.cu import cu_app
from volo_cli.commands.demo import demo_command
from volo_cli.commands.diff import diff_command
from volo_cli.commands.horizon import horizon_command
from volo_cli.commands.init import init_command
from volo_cli.commands.mcp import mcp_app
from volo_cli.commands.migrate import migrate_command
from volo_cli.commands.multiagent import multiagent_app
from volo_cli.commands.pack import pack_app
from volo_cli.commands.persona import persona_app
from volo_cli.commands.record import record_command
from volo_cli.commands.redteam import redteam_app
from volo_cli.commands.run import run_command
from volo_cli.commands.scenarios import scenarios_command
from volo_cli.commands.shadow import shadow_app
from volo_cli.commands.sim import sim_command
from volo_core.env import load_env

__version__ = "0.1.0.dev0"


def _force_utf8_io() -> None:
    """Make stdout/stderr UTF-8 so the CLI never crashes on non-ASCII output under a legacy
    codepage (Windows cp1252 when piped/redirected/in CI). Runs at import — before Click renders
    ``--help`` — so even help text with a stray non-ASCII char is safe. ``errors='replace'`` keeps
    a bad byte from ever raising. No-op where the stream can't be reconfigured (e.g. pytest capture).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            # stream already detached/closed -> nothing we can do, and never worth crashing over
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="replace")


# Runs at import (the console-script imports this module before invoking `app`), so it takes
# effect before Click renders any output — including `--help`.
_force_utf8_io()

app = typer.Typer(
    name="volo",
    help="Volo — a flight simulator for AI agents. See https://github.com/volo.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _version_cb(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_cb,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Volo — record, simulate, score, gate."""
    load_env()  # pick up a local .env (GROQ_API_KEY, VOLO_* flags) before any command runs


app.command("init", help="Quickstart: record an agent and score it in one step.")(init_command)
app.command("record", help="Capture a live agent run as a Recording.")(record_command)
app.command("sim", help="Boot the simulated environment from a recording.")(sim_command)
app.command("scenarios", help="List the default scenario operator library.")(scenarios_command)
app.command("run", help="Run an agent against scenarios; produce a reliability report.")(
    run_command
)
app.command("ci", help="Block PRs that regress reliability (CI entrypoint).")(ci_command)
app.command("comment", help="Render a sticky PR comment (reliability + optional compliance).")(
    comment_command
)
app.command("diff", help="Diff two runs and attribute regressions to a step + commit.")(
    diff_command
)
app.command("migrate", help="Compare an agent's reliability + cost across two models.")(
    migrate_command
)
app.command("horizon", help="Long-horizon drift rig: replay N episodes, surface context rot.")(
    horizon_command
)
app.command("demo", help="Seed the data dir with showcase recordings + reports.")(demo_command)
app.add_typer(mcp_app, name="mcp")
app.add_typer(shadow_app, name="shadow")
app.add_typer(redteam_app, name="redteam")
app.add_typer(persona_app, name="persona")
app.add_typer(pack_app, name="pack")
app.add_typer(compliance_app, name="compliance")
app.add_typer(cu_app, name="cu")
app.add_typer(multiagent_app, name="multiagent")
app.add_typer(certify_app, name="certify")


if __name__ == "__main__":  # pragma: no cover
    app()
