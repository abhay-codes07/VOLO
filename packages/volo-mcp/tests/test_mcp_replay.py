"""MCPReplayServer: recorded traffic replays byte-faithfully; unknowns flag, never hallucinate."""

from __future__ import annotations

from typing import Any

from volo_core import Recording
from volo_mcp import SIM_MISS_CODE, MCPRecorder, MCPReplayServer
from volo_simulator import Tier2Replayer


def _req(msg_id: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def _res(msg_id: int, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _recorded_session() -> Recording:
    """One handshake + listing + two tool calls (one repeated with a different answer) + error."""
    rec = MCPRecorder(server_name="calc")
    convo: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            _req(1, "initialize", {"protocolVersion": "2025-06-18"}),
            _res(1, {"protocolVersion": "2025-06-18", "serverInfo": {"name": "calc"}}),
        ),
        (
            _req(2, "tools/list"),
            _res(2, {"tools": [{"name": "add", "inputSchema": {"type": "object"}}]}),
        ),
        (
            _req(3, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}}),
            _res(3, {"content": [{"type": "text", "text": "3"}], "isError": False}),
        ),
        (
            _req(4, "tools/call", {"name": "flaky", "arguments": {}}),
            _res(4, {"content": [{"type": "text", "text": "first"}], "isError": False}),
        ),
        (
            _req(5, "tools/call", {"name": "flaky", "arguments": {}}),
            _res(5, {"content": [{"type": "text", "text": "second"}], "isError": False}),
        ),
        (
            _req(6, "tools/call", {"name": "boom", "arguments": {}}),
            {"jsonrpc": "2.0", "id": 6, "error": {"code": -32602, "message": "bad params"}},
        ),
    ]
    for request, response in convo:
        rec.on_client_message(request)
        rec.on_server_message(response)
    return rec.recording


def test_recorded_call_replays_identically_with_fresh_ids() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    out = server.handle_message(
        _req(41, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}})
    )
    assert out == {
        "jsonrpc": "2.0",
        "id": 41,
        "result": {"content": [{"type": "text", "text": "3"}], "isError": False},
    }


def test_handshake_and_listing_replay() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    init = server.handle_message(_req(1, "initialize", {"protocolVersion": "2025-06-18"}))
    assert init is not None and init["result"]["serverInfo"] == {"name": "calc"}
    listing = server.handle_message(_req(2, "tools/list"))
    assert listing is not None and listing["result"]["tools"][0]["name"] == "add"


def test_repeated_identical_calls_replay_in_recorded_order() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    first = server.handle_message(_req(10, "tools/call", {"name": "flaky", "arguments": {}}))
    second = server.handle_message(_req(11, "tools/call", {"name": "flaky", "arguments": {}}))
    assert first is not None and first["result"]["content"][0]["text"] == "first"
    assert second is not None and second["result"]["content"][0]["text"] == "second"


def test_recorded_protocol_error_replays_as_error() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    out = server.handle_message(_req(12, "tools/call", {"name": "boom", "arguments": {}}))
    assert out == {
        "jsonrpc": "2.0",
        "id": 12,
        "error": {"code": -32602, "message": "bad params"},
    }


def test_unrecorded_input_flags_sim_miss() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    out = server.handle_message(
        _req(13, "tools/call", {"name": "add", "arguments": {"a": 9, "b": 9}})
    )
    assert out is not None and out["error"]["code"] == SIM_MISS_CODE
    assert out["error"]["data"]["tool"] == "mcp.tool:add"


def test_tier2_env_flags_when_all_synthesizers_abstain() -> None:
    env = Tier2Replayer(_recorded_session(), synthesizers=[])
    server = MCPReplayServer(env)
    out = server.handle_message(_req(14, "tools/call", {"name": "add", "arguments": {"a": 5}}))
    assert out is not None and out["error"]["code"] == SIM_MISS_CODE


def test_notifications_and_stray_responses_get_no_reply() -> None:
    server = MCPReplayServer.from_recording(_recorded_session())
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.handle_message({"jsonrpc": "2.0", "id": 3, "result": {}}) is None


def test_full_session_replay_matches_recorded_responses() -> None:
    """Every recorded exchange, replayed end-to-end, is answered with the exact wire shape."""
    recording = _recorded_session()
    server = MCPReplayServer.from_recording(recording)
    exchanges = [
        (_req(1, "initialize", {"protocolVersion": "2025-06-18"}), "result"),
        (_req(2, "tools/list"), "result"),
        (_req(3, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}}), "result"),
        (_req(4, "tools/call", {"name": "flaky", "arguments": {}}), "result"),
        (_req(5, "tools/call", {"name": "flaky", "arguments": {}}), "result"),
        (_req(6, "tools/call", {"name": "boom", "arguments": {}}), "error"),
    ]
    for step, (request, kind) in zip(recording.steps, exchanges, strict=True):
        reply = server.handle_message(request)
        assert reply is not None and reply["id"] == request["id"]
        assert step.payload.type == "tool_call"
        assert reply[kind] == step.payload.response[kind]
