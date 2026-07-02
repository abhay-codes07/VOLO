"""MCPReplayServer — a simulated MCP server backed by any Volo SimulatedEnvironment.

Point an agent's MCP client at this instead of the real server: recorded traffic replays
byte-faithfully (results *and* protocol errors), un-recorded inputs come back as a JSON-RPC
error with ``SIM_MISS_CODE`` — the flag-on-unknown invariant (ADR-0009) at the MCP boundary.

Transport-free by design: ``handle_message`` maps one client message to at most one response
message. Slice 2 wires this behind a stdio loop (``volo mcp serve``).
"""

from __future__ import annotations

from typing import Any

from volo_core import Recording
from volo_core.interfaces import SimulatedEnvironment, ToolRegistry
from volo_mcp.messages import (
    SIM_MISS_CODE,
    error_response,
    is_request,
    response_from_envelope,
    tool_key,
)
from volo_simulator import Tier1Replayer


class MCPReplayServer:
    """Answers MCP JSON-RPC requests from a simulated environment instead of the real world."""

    def __init__(self, env: SimulatedEnvironment) -> None:
        self._env = env
        self._tools: ToolRegistry = env.tool_registry()

    @classmethod
    def from_recording(cls, recording: Recording) -> MCPReplayServer:
        """Tier-1 (pure cache-replay) server. For Tier-2, construct the env yourself and pass it."""
        return cls(Tier1Replayer(recording))

    def handle_message(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        """Map one client → server message to a response message (or ``None`` to send nothing).

        Notifications and client responses (to server-initiated requests) produce no reply,
        matching JSON-RPC semantics.
        """
        if not is_request(msg):
            return None
        msg_id = msg["id"]
        method = str(msg["method"])
        params = msg.get("params")
        tool, request = tool_key(method, params if isinstance(params, dict) else None)
        try:
            stored = self._tools.call(tool, request)
        except LookupError as exc:  # ReplayMiss / Tier2Miss — refuse to hallucinate
            return error_response(
                msg_id,
                SIM_MISS_CODE,
                f"Volo sim miss: no recorded or synthesizable response for {method!r}. {exc}",
                data={"tool": tool, "request": request},
            )
        return response_from_envelope(msg_id, stored)
