"""Conformance: a recording is a behavioral contract the live server must still honor."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any, cast

from volo_core import Recording, ToolCallPayload
from volo_mcp import StdioRecordProxy, check_conformance, encode_message

REPO_ROOT = Path(__file__).resolve().parents[3]
CALC_SERVER = REPO_ROOT / "examples" / "mcp_calc_server.py"
SERVER_CMD = [sys.executable, "-u", str(CALC_SERVER)]

SESSION: list[dict[str, Any]] = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    },
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 2, "b": 40}},
    },
    {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    },
]


def _record() -> Recording:
    proxy = StdioRecordProxy(
        SERVER_CMD,
        server_name="mcp-calc",
        client_in=io.BytesIO(b"".join(encode_message(m) for m in SESSION)),
        client_out=io.BytesIO(),
    )
    return proxy.run()


def test_unchanged_server_conforms() -> None:
    report = check_conformance(_record(), SERVER_CMD)
    assert report.passed
    assert report.counts() == {"identical": 4, "different": 0, "no_reply": 0}
    # recorded protocol errors count as behavior and must match too
    assert any(v.tool == "mcp.tool:nope" and v.verdict == "identical" for v in report.verdicts)


def test_changed_behavior_is_flagged() -> None:
    recording = _record()
    # simulate a server regression: the recording expects a different answer than the live server
    add_step = next(
        cast(ToolCallPayload, s.payload)
        for s in recording.steps
        if cast(ToolCallPayload, s.payload).tool == "mcp.tool:add"
    )
    add_step.response = {"result": {"content": [{"type": "text", "text": "43"}], "isError": False}}

    report = check_conformance(recording, SERVER_CMD)
    assert not report.passed
    counts = report.counts()
    assert counts["different"] == 1 and counts["identical"] == 3
    assert report.to_dict()["passed"] is False


def test_empty_recording_passes_vacuously() -> None:
    report = check_conformance(Recording(), SERVER_CMD)
    assert report.passed and report.verdicts == []
