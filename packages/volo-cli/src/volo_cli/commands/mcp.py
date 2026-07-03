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
        f"{proxy.framing_errors} framing error(s) -> {path}",
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
        f" from {len(recording.steps)} recorded step(s) - Ctrl-D / client hang-up to stop",
        err=True,
    )
    replies = serve_stdio(server, sys.stdin.buffer, sys.stdout.buffer)
    typer.echo(f"mcp serve: session over - {replies} repl(y/ies) served", err=True)


@mcp_app.command("fuzz")
def mcp_fuzz(
    recording_path: Annotated[Path, typer.Argument(help="Path to a Recording JSON file.")],
    op: Annotated[
        str | None,
        typer.Option("--op", help="Run a single operator (default: the whole MCP fuzz library)."),
    ] = None,
    seed: Annotated[int, typer.Option("--seed", help="Base seed — same seed, same mutations.")] = 0,
    serve: Annotated[
        bool,
        typer.Option("--serve", help="Serve ONE mutated sim over stdio instead of writing files."),
    ] = False,
    out_dir: Annotated[
        Path | None,
        typer.Option("--out-dir", help="Where to write mutated recordings (default <rec>-fuzz/)."),
    ] = None,
    report: Annotated[
        Path | None,
        typer.Option("--report", help="Also write a JSON fuzz report."),
    ] = None,
) -> None:
    """Mutate recorded MCP tool responses with the adversarial scenario operators."""
    import json

    from volo_mcp.fuzz import default_mcp_fuzz_library, fuzz_change_summary, mcp_fuzz_scenarios
    from volo_mcp.replay import MCPReplayServer
    from volo_mcp.stdio import serve_stdio

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    recording = Recording.from_json(recording_path.read_text(encoding="utf-8"))

    library = default_mcp_fuzz_library(seed=seed)
    if op is not None:
        library = [o for o in library if o.name == op]
        if not library:
            names = ", ".join(o.name for o in default_mcp_fuzz_library())
            raise typer.BadParameter(f"Unknown --op {op!r}. Available: {names}")
    scenarios = mcp_fuzz_scenarios(recording, seed=seed, ops=library)

    if serve:
        if len(scenarios) != 1:
            raise typer.BadParameter("--serve needs exactly one operator — pass --op <name>.")
        scenario, mutated = scenarios[0]
        typer.echo(
            f"mcp fuzz: serving {scenario.op_name!r} (seed {scenario.seed}, "
            f"failure class {scenario.failure_class}) - Ctrl-D / client hang-up to stop",
            err=True,
        )
        replies = serve_stdio(
            MCPReplayServer.from_recording(mutated), sys.stdin.buffer, sys.stdout.buffer
        )
        typer.echo(f"mcp fuzz: session over - {replies} repl(y/ies) served", err=True)
        return

    target_dir = out_dir or recording_path.parent / f"{recording_path.stem}-fuzz"
    target_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for scenario, mutated in scenarios:
        changes = fuzz_change_summary(recording, mutated)
        path = target_dir / f"{recording_path.stem}.{scenario.op_name}.seed{scenario.seed}.json"
        path.write_text(mutated.to_json() + "\n", encoding="utf-8")
        entries.append(
            {
                "op": scenario.op_name,
                "seed": scenario.seed,
                "failure_class": scenario.failure_class,
                "file": str(path),
                "changes": changes,
            }
        )
        typer.echo(
            f"mcp fuzz: {scenario.op_name:18} [{scenario.failure_class}] "
            f"{len(changes)} change(s) -> {path.name}"
        )
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"scenarios": entries}, indent=2) + "\n", encoding="utf-8")
        typer.echo(f"mcp fuzz: report -> {report}")
    typer.echo(f"mcp fuzz: serve any of these with `volo mcp serve <file>` (dir: {target_dir})")


@mcp_app.command("conformance")
def mcp_conformance(
    recording_path: Annotated[Path, typer.Argument(help="Path to a Recording JSON file.")],
    server_cmd: Annotated[
        list[str],
        typer.Argument(help="The live MCP server command to test (put it after `--`)."),
    ],
    report: Annotated[
        Path | None,
        typer.Option("--report", help="Also write the JSON conformance report."),
    ] = None,
) -> None:
    """Replay recorded requests against the LIVE server; fail if behavior changed."""
    import json

    from volo_mcp.conformance import check_conformance

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    recording = Recording.from_json(recording_path.read_text(encoding="utf-8"))

    result = check_conformance(recording, list(server_cmd))
    for v in result.verdicts:
        marker = "ok " if v.verdict == "identical" else "!! "
        typer.echo(f"mcp conformance: {marker}[{v.index:03d}] {v.tool:32} {v.verdict}")
    counts = result.counts()
    typer.echo(
        f"mcp conformance: {counts['identical']} identical, {counts['different']} different, "
        f"{counts['no_reply']} no-reply -> {'PASS' if result.passed else 'FAIL'}"
    )
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
        typer.echo(f"mcp conformance: report -> {report}")
    if not result.passed:
        raise typer.Exit(1)
