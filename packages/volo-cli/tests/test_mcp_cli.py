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


def _record_fixture(tmp_path: Path) -> Path:
    out = tmp_path / "calc.json"
    res = runner.invoke(
        app,
        ["mcp", "record", "--out", str(out), "--", sys.executable, "-u", str(CALC_SERVER)],
        input=CLIENT_INPUT,
    )
    assert res.exit_code == 0, res.output
    return out


def test_mcp_fuzz_writes_mutated_recordings_and_report(tmp_path: Path) -> None:
    rec = _record_fixture(tmp_path)
    fuzz_dir = tmp_path / "fuzzed"
    report = tmp_path / "fuzz-report.json"

    res = runner.invoke(
        app,
        ["mcp", "fuzz", str(rec), "--out-dir", str(fuzz_dir), "--report", str(report)],
    )
    assert res.exit_code == 0, res.output
    files = sorted(p.name for p in fuzz_dir.glob("*.json"))
    assert len(files) == 4 and any("corrupt_field" in f for f in files)
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert {e["op"] for e in blob["scenarios"]} == {
        "drop_tool_result",
        "corrupt_field",
        "prompt_injection",
        "reorder_steps",
    }
    # every mutated file is itself a valid, servable recording
    mutated = json.loads((fuzz_dir / files[0]).read_text(encoding="utf-8"))
    assert mutated["recording_schema_version"] == "1.0.0"


def test_mcp_fuzz_unknown_op_fails() -> None:
    res = runner.invoke(app, ["mcp", "fuzz", "x.json", "--op", "nope"])
    assert res.exit_code != 0


def test_mcp_conformance_pass_and_fail(tmp_path: Path) -> None:
    rec = _record_fixture(tmp_path)

    ok = runner.invoke(
        app, ["mcp", "conformance", str(rec), "--", sys.executable, "-u", str(CALC_SERVER)]
    )
    assert ok.exit_code == 0, ok.output
    assert "PASS" in ok.output

    # break the contract: recording now expects an answer the live server won't give
    blob = json.loads(rec.read_text(encoding="utf-8"))
    for step in blob["steps"]:
        if step["payload"]["tool"] == "mcp.tool:add":
            step["payload"]["response"] = {"result": {"content": [], "isError": True}}
    rec.write_text(json.dumps(blob), encoding="utf-8")

    bad = runner.invoke(
        app, ["mcp", "conformance", str(rec), "--", sys.executable, "-u", str(CALC_SERVER)]
    )
    assert bad.exit_code == 1
    assert "FAIL" in bad.output
