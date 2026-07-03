"""Stdio transport: proxy-record a real subprocess server, then replay it byte-faithfully."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

from volo_mcp import (
    SIM_MISS_CODE,
    MCPRecorder,
    MCPReplayServer,
    MessageBuffer,
    StdioRecordProxy,
    encode_message,
    serve_stdio,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CALC_SERVER = REPO_ROOT / "examples" / "mcp_calc_server.py"

CLIENT_SESSION: list[dict[str, Any]] = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    },
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
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


def _session_bytes() -> bytes:
    return b"".join(encode_message(m) for m in CLIENT_SESSION)


def _record_live_session() -> tuple[StdioRecordProxy, list[dict[str, Any]]]:
    """Run the calc server for real behind the proxy; return proxy + the replies the client saw."""
    client_out = io.BytesIO()
    proxy = StdioRecordProxy(
        [sys.executable, "-u", str(CALC_SERVER)],
        server_name="mcp-calc",
        client_in=io.BytesIO(_session_bytes()),
        client_out=client_out,
    )
    proxy.run()
    replies = MessageBuffer().feed(client_out.getvalue())
    return proxy, replies


def test_proxy_passes_through_and_records() -> None:
    proxy, replies = _record_live_session()

    # the client saw one reply per request (notification gets none), untouched
    assert [r["id"] for r in replies] == [1, 2, 3, 4]
    assert replies[2]["result"]["content"][0]["text"] == "42"
    assert replies[3]["error"]["code"] == -32602  # real server error, passed through

    rec = proxy.recorder.recording
    assert [s.payload.tool for s in rec.steps] == [
        "mcp:initialize",
        "mcp:tools/list",
        "mcp.tool:add",
        "mcp.tool:nope",
    ]
    assert proxy.recorder.stats.client_notifications == 1
    assert proxy.framing_errors == 0
    # tools/list was distilled into Tier-2 fuel
    assert {s.name for s in rec.tool_specs} == {"mcp.tool:add", "mcp.tool:multiply"}
    assert rec.agent_meta.extra["mcp_server_info"]["name"] == "mcp-calc"


def test_recorded_session_replays_identically_offline() -> None:
    """The M10 acceptance test: live replies == simulated replies, byte-for-byte."""
    proxy, live_replies = _record_live_session()

    sim_out = io.BytesIO()
    server = MCPReplayServer.from_recording(proxy.recorder.recording)
    replies = serve_stdio(server, io.BytesIO(_session_bytes()), sim_out)

    assert replies == len(live_replies)
    sim_replies = MessageBuffer().feed(sim_out.getvalue())
    assert sim_replies == live_replies


def test_serve_stdio_flags_unrecorded_input_and_survives_garbage() -> None:
    proxy, _ = _record_live_session()
    server = MCPReplayServer.from_recording(proxy.recorder.recording)

    unknown = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 1, "b": 1}},
    }
    out = io.BytesIO()
    replies = serve_stdio(server, io.BytesIO(b"{garbage}\n" + encode_message(unknown)), out)

    assert replies == 1
    (reply,) = MessageBuffer().feed(out.getvalue())
    assert reply["error"]["code"] == SIM_MISS_CODE


def test_proxy_save_roundtrip(tmp_path: Path) -> None:
    proxy, _ = _record_live_session()
    path = proxy.save(tmp_path / "calc.json")
    from volo_core import Recording

    loaded = Recording.from_json(path.read_text(encoding="utf-8"))
    assert len(loaded.steps) == 4
    assert loaded.agent_meta.framework == "mcp"


def test_proxy_recorder_can_be_injected() -> None:
    recorder = MCPRecorder(server_name="custom")
    proxy = StdioRecordProxy(
        [sys.executable, "-u", str(CALC_SERVER)],
        recorder=recorder,
        client_in=io.BytesIO(encode_message({"jsonrpc": "2.0", "id": 1, "method": "ping"})),
        client_out=io.BytesIO(),
    )
    proxy.run()
    assert recorder.recording.steps[0].payload.tool == "mcp:ping"
