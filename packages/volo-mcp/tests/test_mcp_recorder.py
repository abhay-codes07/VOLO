"""MCPRecorder: JSON-RPC traffic in, ordinary Volo Recording (+ ToolSpecs, handshake meta) out."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from volo_core import Recording
from volo_mcp import MCPRecorder


def _req(msg_id: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def _res(msg_id: int, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def test_tools_call_becomes_tool_call_step() -> None:
    rec = MCPRecorder(server_name="calc")
    rec.on_client_message(_req(1, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}}))
    rec.on_server_message(_res(1, {"content": [{"type": "text", "text": "3"}], "isError": False}))

    steps = rec.recording.steps
    assert len(steps) == 1
    payload = steps[0].payload
    assert payload.type == "tool_call"
    assert payload.tool == "mcp.tool:add"
    assert payload.request == {"a": 1, "b": 2}
    assert payload.response == {
        "result": {"content": [{"type": "text", "text": "3"}], "isError": False}
    }


def test_meta_methods_recorded_with_mcp_prefix() -> None:
    rec = MCPRecorder()
    rec.on_client_message(_req(1, "resources/read", {"uri": "file:///a.txt"}))
    rec.on_server_message(_res(1, {"contents": []}))
    assert rec.recording.steps[0].payload.tool == "mcp:resources/read"


def test_initialize_meta_harvested() -> None:
    rec = MCPRecorder(server_name="calc")
    rec.on_client_message(_req(1, "initialize", {"protocolVersion": "2025-06-18"}))
    rec.on_server_message(
        _res(1, {"protocolVersion": "2025-06-18", "serverInfo": {"name": "calc", "version": "1.0"}})
    )
    extra = rec.recording.agent_meta.extra
    assert extra["mcp_server_name"] == "calc"
    assert extra["mcp_protocol_version"] == "2025-06-18"
    assert extra["mcp_server_info"] == {"name": "calc", "version": "1.0"}


def test_tools_list_distilled_into_tool_specs() -> None:
    rec = MCPRecorder()
    schema = {"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}
    rec.on_client_message(_req(1, "tools/list"))
    rec.on_server_message(
        _res(1, {"tools": [{"name": "add", "description": "adds", "inputSchema": schema}]})
    )
    # a second listing must not duplicate specs
    rec.on_client_message(_req(2, "tools/list"))
    rec.on_server_message(_res(2, {"tools": [{"name": "add", "inputSchema": schema}]}))

    specs = rec.recording.tool_specs
    assert [s.name for s in specs] == ["mcp.tool:add"]
    assert specs[0].description == "adds"
    assert specs[0].input_schema == schema
    assert rec.stats.tool_specs_captured == 1


def test_error_response_recorded_as_error_envelope() -> None:
    rec = MCPRecorder()
    rec.on_client_message(_req(1, "tools/call", {"name": "boom", "arguments": {}}))
    rec.on_server_message(
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad params"}}
    )
    payload = rec.recording.steps[0].payload
    assert payload.type == "tool_call"
    assert payload.response == {"error": {"code": -32602, "message": "bad params"}}


def test_notifications_and_orphans_counted_not_recorded() -> None:
    rec = MCPRecorder()
    rec.on_client_message({"jsonrpc": "2.0", "method": "notifications/initialized"})
    rec.on_server_message({"jsonrpc": "2.0", "method": "notifications/progress", "params": {}})
    rec.on_server_message(_res(99, {"never": "requested"}))
    rec.on_server_message(_req(5, "sampling/createMessage", {}))

    assert rec.recording.steps == []
    assert rec.stats.client_notifications == 1
    assert rec.stats.server_notifications == 1
    assert rec.stats.orphan_responses == 1
    assert rec.stats.server_requests == 1


def test_save_roundtrips_through_recording_schema(tmp_path: Path) -> None:
    rec = MCPRecorder(server_name="calc")
    rec.on_client_message(_req(1, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}}))
    rec.on_server_message(_res(1, {"content": [], "isError": False}))
    out = rec.save(tmp_path / "mcp.json")

    loaded = Recording.from_json(out.read_text(encoding="utf-8"))
    assert loaded.agent_meta.framework == "mcp"
    assert loaded.steps[0].payload.tool == "mcp.tool:add"
