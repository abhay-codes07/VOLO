"""`volo mcp` — record and replay Model Context Protocol servers (newplan P1 / ADR-0014).

stdout is the MCP wire in both subcommands; every human-facing line goes to stderr.

* ``volo mcp record --out rec.json -- python my_server.py`` — transparent proxy: your client
  talks through us to the real server; on hang-up the session is saved as a Recording.
* ``volo mcp serve rec.json`` — a simulated MCP server: recorded answers replay exactly,
  un-recorded inputs return JSON-RPC error -32042 instead of a hallucination.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from volo_core import Recording

mcp_app = typer.Typer(
    name="mcp",
    help="Record / replay MCP servers deterministically.",
    no_args_is_help=True,
)


@mcp_app.command("record")
def mcp_record(
    server_cmd: Annotated[
        list[str],
        typer.Argument(help="The real MCP server command (put it after `--`)."),
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Recording path (default ./.volo/recordings/<id>.json)."),
    ] = None,
    server_name: Annotated[
        str | None,
        typer.Option("--server-name", help="Name stored in the recording metadata."),
    ] = None,
) -> None:
    """Proxy a live MCP session to the real server and record it."""
    from volo_mcp.stdio import StdioRecordProxy

    proxy = StdioRecordProxy(
        list(server_cmd),
        server_name=server_name,
        client_in=sys.stdin.buffer,
        client_out=sys.stdout.buffer,
    )
    recording = proxy.run()
    path = proxy.save(out)
    stats = proxy.recorder.stats
    typer.echo(
        f"mcp record: {len(recording.steps)} step(s), {stats.tool_specs_captured} tool spec(s), "
        f"{proxy.framing_errors} framing error(s) → {path}",
        err=True,
    )


@mcp_app.command("serve")
def mcp_serve(
    recording_path: Annotated[Path, typer.Argument(help="Path to a Recording JSON file.")],
) -> None:
    """Serve a simulated MCP server (Tier-1 replay) from a recording, over stdio."""
    from volo_mcp.replay import MCPReplayServer
    from volo_mcp.stdio import serve_stdio

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    recording = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    server = MCPReplayServer.from_recording(recording)
    typer.echo(
        f"mcp serve: simulating {recording.agent_meta.extra.get('mcp_server_name', 'mcp-server')!r}"
        f" from {len(recording.steps)} recorded step(s) — Ctrl-D / client hang-up to stop",
        err=True,
    )
    replies = serve_stdio(server, sys.stdin.buffer, sys.stdout.buffer)
    typer.echo(f"mcp serve: session over — {replies} repl(y/ies) served", err=True)
