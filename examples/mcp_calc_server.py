"""A tiny, dependency-free stdio MCP server used by tests, docs, and the M10 demo.

Speaks just enough MCP (newline-delimited JSON-RPC 2.0) to exercise the volo-mcp pipeline:
``initialize``, ``tools/list``, and ``tools/call`` for two deterministic tools (``add``,
``multiply``). Unknown tools/methods return proper JSON-RPC errors — which the recorder must
capture and the replayer must reproduce.

Run directly:  ``python examples/mcp_calc_server.py``  (reads stdin, writes stdout).
"""

from __future__ import annotations

import json
import sys
from typing import Any

PROTOCOL_VERSION = "2025-06-18"

TOOLS: list[dict[str, Any]] = [
    {
        "name": "add",
        "description": "Add two numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
]


def _handle(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Return ``{"result": ...}`` or ``{"error": ...}`` for one request."""
    if method == "initialize":
        return {
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-calc", "version": "1.0.0"},
            }
        }
    if method == "tools/list":
        return {"result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "add":
            value = args.get("a", 0) + args.get("b", 0)
        elif name == "multiply":
            value = args.get("a", 0) * args.get("b", 0)
        else:
            return {"error": {"code": -32602, "message": f"unknown tool: {name!r}"}}
        return {"result": {"content": [{"type": "text", "text": str(value)}], "isError": False}}
    if method == "ping":
        return {"result": {}}
    return {"error": {"code": -32601, "message": f"method not found: {method!r}"}}


def main() -> None:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    for line in iter(stdin.readline, b""):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict) or "method" not in msg or "id" not in msg:
            continue  # notifications need no reply; anything else is noise
        reply: dict[str, Any] = {"jsonrpc": "2.0", "id": msg["id"]}
        reply.update(_handle(str(msg["method"]), msg.get("params") or {}))
        stdout.write(json.dumps(reply, separators=(",", ":")).encode("utf-8") + b"\n")
        stdout.flush()


if __name__ == "__main__":
    main()
