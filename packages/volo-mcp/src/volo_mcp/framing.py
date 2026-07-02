"""MCP stdio framing — incremental newline-delimited JSON-RPC decoding/encoding.

The MCP stdio transport delimits JSON-RPC 2.0 messages with newlines. ``MessageBuffer`` is a
pure, incremental decoder (feed bytes in any chunking, get whole messages out) so transports can
stay dumb pipes and everything else stays testable without I/O.
"""

from __future__ import annotations

import json
from typing import Any


class FramingError(ValueError):
    """A line crossed the wire that is not a JSON-RPC message object."""


def encode_message(msg: dict[str, Any]) -> bytes:
    """Serialize one JSON-RPC message for the stdio transport (compact JSON + newline)."""
    return (json.dumps(msg, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


class MessageBuffer:
    """Incremental ndjson decoder. Feed arbitrary byte chunks; whole messages come out in order."""

    def __init__(self) -> None:
        self._buf = b""

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        """Consume a chunk and return every complete message it (plus buffered bytes) contains."""
        self._buf += data
        out: list[dict[str, Any]] = []
        while (idx := self._buf.find(b"\n")) != -1:
            line, self._buf = self._buf[:idx], self._buf[idx + 1 :]
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise FramingError(f"undecodable JSON-RPC line: {stripped[:200]!r}") from exc
            if not isinstance(parsed, dict):
                raise FramingError(
                    f"JSON-RPC message must be an object, got {type(parsed).__name__}"
                )
            out.append(parsed)
        return out

    @property
    def pending_bytes(self) -> int:
        """Bytes buffered that do not yet form a complete line."""
        return len(self._buf)
