"""MCPRecorder — transport-free capture of MCP traffic into an ordinary Volo Recording.

Feed it every JSON-RPC message that crosses the client↔server boundary (``on_client_message`` /
``on_server_message``); it pairs requests with responses by id and appends ``tool_call`` steps.
Two fidelity bonuses fall out for free:

* a recorded ``tools/list`` response is distilled into ``ToolSpec`` entries (name, description,
  input/output schema), which is exactly what the Tier-2 simulator feeds on;
* the ``initialize`` result (protocol version, server info) is kept in ``agent_meta.extra`` so a
  replayed handshake is byte-faithful.

Transports (stdio proxy, HTTP) land in M10 slice 2 and stay dumb: bytes → ``MessageBuffer`` →
these two methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from volo_core import Recording, ToolSpec
from volo_core.recording import ToolCallPayload
from volo_mcp.messages import (
    INITIALIZE_METHOD,
    TOOL_PREFIX,
    TOOLS_LIST_METHOD,
    MsgId,
    envelope,
    is_notification,
    is_request,
    is_response,
    tool_key,
)
from volo_sdk import Recorder


@dataclass
class MCPRecorderStats:
    """Counters for everything seen on the wire, including what we deliberately skip."""

    requests: int = 0
    responses: int = 0
    client_notifications: int = 0
    server_notifications: int = 0
    server_requests: int = 0  # server→client (e.g. sampling/createMessage) — not recorded in v1
    orphan_responses: int = 0  # response ids we never saw a request for
    tool_specs_captured: int = 0
    _pending_ids: set[MsgId] = field(default_factory=set)


class MCPRecorder:
    """Pairs JSON-RPC requests/responses and writes them as ``tool_call`` steps."""

    def __init__(
        self, *, server_name: str = "mcp-server", recorder: Recorder | None = None
    ) -> None:
        self._recorder = recorder or Recorder(agent_name=server_name, framework="mcp")
        self._recorder.recording.agent_meta.extra.setdefault("mcp_server_name", server_name)
        # id → (payload to fill, original method) for requests still awaiting a response
        self._pending: dict[MsgId, tuple[ToolCallPayload, str]] = {}
        self.stats = MCPRecorderStats()

    # ---- feed the two directions ----

    def on_client_message(self, msg: dict[str, Any]) -> None:
        """A message travelling client → server."""
        if is_request(msg):
            self.stats.requests += 1
            method = str(msg["method"])
            params = msg.get("params")
            tool, request = tool_key(method, params if isinstance(params, dict) else None)
            payload = ToolCallPayload(tool=tool, request=request)
            self._recorder.record_step(payload)
            self._pending[self._msg_id(msg)] = (payload, method)
        elif is_notification(msg):
            self.stats.client_notifications += 1
        elif is_response(msg):
            # client answering a server→client request; the request itself wasn't recorded
            self.stats.responses += 1

    def on_server_message(self, msg: dict[str, Any]) -> None:
        """A message travelling server → client."""
        if is_response(msg):
            self.stats.responses += 1
            pending = self._pending.pop(self._msg_id(msg), None)
            if pending is None:
                self.stats.orphan_responses += 1
                return
            payload, method = pending
            payload.response = envelope(msg)
            if "error" not in payload.response:
                self._harvest_meta(method, msg.get("result"))
        elif is_notification(msg):
            self.stats.server_notifications += 1
        elif is_request(msg):
            self.stats.server_requests += 1

    # ---- results ----

    @property
    def recording(self) -> Recording:
        return self._recorder.recording

    def save(self, path: Path | str | None = None) -> Path:
        """Persist via the SDK Recorder (redaction pass included by default)."""
        return self._recorder.save(path)

    # ---- internals ----

    @staticmethod
    def _msg_id(msg: dict[str, Any]) -> MsgId:
        raw = msg.get("id")
        return raw if isinstance(raw, int | str) else str(raw)

    def _harvest_meta(self, method: str, result: Any) -> None:
        """Distill protocol responses into simulator-fuel (ToolSpecs, handshake meta)."""
        if not isinstance(result, dict):
            return
        if method == TOOLS_LIST_METHOD:
            self._capture_tool_specs(result)
        elif method == INITIALIZE_METHOD:
            extra = self._recorder.recording.agent_meta.extra
            if "protocolVersion" in result:
                extra["mcp_protocol_version"] = result["protocolVersion"]
            if "serverInfo" in result:
                extra["mcp_server_info"] = result["serverInfo"]

    def _capture_tool_specs(self, result: dict[str, Any]) -> None:
        tools = result.get("tools")
        if not isinstance(tools, list):
            return
        known = {spec.name for spec in self._recorder.recording.tool_specs}
        for entry in tools:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            name = f"{TOOL_PREFIX}{entry['name']}"
            if name in known:
                continue
            spec = ToolSpec(
                name=name,
                description=entry.get("description"),
                input_schema=entry.get("inputSchema"),
                output_schema=entry.get("outputSchema"),
            )
            self._recorder.recording.tool_specs.append(spec)
            known.add(name)
            self.stats.tool_specs_captured += 1
