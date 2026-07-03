"""`volo mcp record|serve` — the CLI shell over the stdio transport."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from volo_cli.main import app

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parents[3]
CALC_SERVER = REPO_ROOT / "examples" / "mcp_calc_server.py"


def _ndjson(*messages: dict) -> str:
    return "".join(json.dumps(m, separators=(",", ":")) + "\n" for m in messages)


CLIENT_INPUT = _ndjson(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    },
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 20, "b": 22}},
    },
)


def test_mcp_help_lists_subcommands() -> None:
    res = runner.invoke(app, ["mcp", "--help"])
    assert res.exit_code == 0, res.output
    assert "record" in res.output and "serve" in res.output


def test_mcp_record_then_serve_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "calc.json"

    rec_res = runner.invoke(
        app,
        ["mcp", "record", "--out", str(out), "--", sys.executable, "-u", str(CALC_SERVER)],
        input=CLIENT_INPUT,
    )
    assert rec_res.exit_code == 0, rec_res.output
    assert out.exists()
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert [s["payload"]["tool"] for s in blob["steps"]] == ["mcp:initialize", "mcp.tool:add"]

    serve_res = runner.invoke(app, ["mcp", "serve", str(out)], input=CLIENT_INPUT)
    assert serve_res.exit_code == 0, serve_res.output
    lines = [ln for ln in serve_res.stdout.splitlines() if ln.startswith("{")]
    replies = [json.loads(ln) for ln in lines]
    assert replies[1]["result"]["content"][0]["text"] == "42"


def test_mcp_serve_missing_recording_fails() -> None:
    res = runner.invoke(app, ["mcp", "serve", "does-not-exist.json"])
    assert res.exit_code != 0
