"""JSON-RPC 2.0 / MCP message taxonomy — the one module that understands MCP methods.

Everything protocol-version-sensitive lives here (newplan §6 risk 1): if the MCP spec moves,
this is the only file that should have to.

The load-bearing idea is ``tool_key``: every MCP request is mapped onto the ``(tool, request)``
pair that ``volo_core.cache_key`` already keys on, so recordings of MCP traffic are ordinary
Volo recordings and the whole Tier-1/Tier-2 simulator stack applies unchanged.
"""

from __future__ import annotations

from typing import Any

JSONRPC_VERSION = "2.0"

# JSON-RPC reserves -32000..-32099 for implementation-defined server errors.
SIM_MISS_CODE = -32042
"""Returned when the simulator has no recorded/synthesizable answer. Never hallucinate."""

TOOL_CALL_METHOD = "tools/call"
TOOLS_LIST_METHOD = "tools/list"
INITIALIZE_METHOD = "initialize"

# Prefixes for the two kinds of cache identity an MCP request can have.
TOOL_PREFIX = "mcp.tool:"  # a real tool invocation (tools/call), keyed by tool name
META_PREFIX = "mcp:"  # protocol/meta methods (initialize, tools/list, resources/read, ...)

MsgId = int | str


def is_request(msg: dict[str, Any]) -> bool:
    return "method" in msg and "id" in msg


def is_notification(msg: dict[str, Any]) -> bool:
    return "method" in msg and "id" not in msg


def is_response(msg: dict[str, Any]) -> bool:
    return "method" not in msg and "id" in msg and ("result" in msg or "error" in msg)


def tool_key(method: str, params: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Map an MCP request onto the ``(tool, request)`` identity Volo caches on.

    ``tools/call`` keys on the *tool name + arguments* (so the same logical call recorded via
    different request ids replays correctly); every other method keys on the method + params.
    """
    p = params or {}
    if method == TOOL_CALL_METHOD:
        name = str(p.get("name", ""))
        args = p.get("arguments") or {}
        request = dict(args) if isinstance(args, dict) else {"arguments": args}
        return f"{TOOL_PREFIX}{name}", request
    return f"{META_PREFIX}{method}", dict(p)


def envelope(msg: dict[str, Any]) -> dict[str, Any]:
    """Store a JSON-RPC response as a ``{"result": ...}`` or ``{"error": ...}`` envelope.

    ``ToolCallPayload.response`` must round-trip *both* successful results and protocol errors
    (an error from the real server is real behavior the sim must reproduce), so the recorded
    response is always one of the two envelope shapes.
    """
    if "error" in msg:
        return {"error": msg["error"]}
    return {"result": msg.get("result")}


def response_from_envelope(msg_id: MsgId, stored: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the wire-shape JSON-RPC response for a stored envelope."""
    if "error" in stored:
        return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "error": stored["error"]}
    return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "result": stored.get("result")}


def error_response(
    msg_id: MsgId,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "error": err}
