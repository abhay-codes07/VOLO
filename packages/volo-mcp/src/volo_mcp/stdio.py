"""Stdio transport — the recording proxy and the replay serve-loop (M10 slice 2).

Two thin shells around the transport-free cores:

* ``StdioRecordProxy`` — sits transparently between an MCP client and the *real* server (spawned
  as a subprocess): every byte passes through untouched, and both directions are teed into an
  ``MCPRecorder``. When the client hangs up, the recording is complete.
* ``serve_stdio`` — the inverse: reads client messages from a stream, answers them from an
  ``MCPReplayServer``, and writes responses back. Point an MCP client at ``volo mcp serve`` and
  it talks to the simulation instead of the real world.

Both take explicit binary streams so tests drive them with in-memory pipes; the CLI passes
``sys.stdin.buffer`` / ``sys.stdout.buffer``. Diagnostics never touch the data streams — stdout
is protocol, stderr is for humans.
"""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from volo_core import Recording
from volo_mcp.framing import FramingError, MessageBuffer, encode_message
from volo_mcp.recorder import MCPRecorder
from volo_mcp.replay import MCPReplayServer


class StdioRecordProxy:
    """Transparent tee: client ⇄ (this proxy) ⇄ real MCP server subprocess.

    Pass-through is byte-exact (raw lines are forwarded, never re-encoded); recording is
    best-effort on top — a line that fails to parse is still forwarded and counted in
    ``framing_errors`` rather than breaking the session.
    """

    def __init__(
        self,
        server_cmd: list[str],
        *,
        server_name: str | None = None,
        recorder: MCPRecorder | None = None,
        client_in: BinaryIO,
        client_out: BinaryIO,
        shutdown_timeout_s: float = 10.0,
    ) -> None:
        if not server_cmd:
            raise ValueError("server_cmd must name the real MCP server executable")
        self._cmd = server_cmd
        self.recorder = recorder or MCPRecorder(server_name=server_name or server_cmd[0])
        self._client_in = client_in
        self._client_out = client_out
        self._timeout = shutdown_timeout_s
        self.framing_errors = 0

    def run(self) -> Recording:
        """Pump both directions until the client closes its side; return the Recording."""
        proc = subprocess.Popen(
            self._cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # server logs pass through to our stderr
            bufsize=0,
        )
        assert proc.stdin is not None and proc.stdout is not None
        reader = threading.Thread(
            target=self._pump_server_to_client, args=(proc.stdout,), daemon=True
        )
        reader.start()
        try:
            buf = MessageBuffer()
            for line in iter(self._client_in.readline, b""):
                proc.stdin.write(line)
                proc.stdin.flush()
                self._tee(buf, line, self.recorder.on_client_message)
        finally:
            proc.stdin.close()  # EOF → a well-behaved server drains and exits
            try:
                proc.wait(timeout=self._timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            reader.join(timeout=self._timeout)
        return self.recorder.recording

    def save(self, path: Path | str | None = None) -> Path:
        return self.recorder.save(path)

    # ---- internals ----

    def _pump_server_to_client(self, server_out: BinaryIO) -> None:
        buf = MessageBuffer()
        for line in iter(server_out.readline, b""):
            self._client_out.write(line)
            self._client_out.flush()
            self._tee(buf, line, self.recorder.on_server_message)

    def _tee(
        self,
        buf: MessageBuffer,
        line: bytes,
        sink: Callable[[dict[str, Any]], None],
    ) -> None:
        try:
            for msg in buf.feed(line):
                sink(msg)
        except FramingError:
            self.framing_errors += 1


def serve_stdio(server: MCPReplayServer, in_stream: BinaryIO, out_stream: BinaryIO) -> int:
    """Answer newline-delimited JSON-RPC from ``in_stream`` until EOF; return replies written.

    Malformed lines are skipped (a simulated server must not crash mid-suite on one bad line);
    notifications produce no reply, matching JSON-RPC semantics.
    """
    buf = MessageBuffer()
    replies = 0
    for line in iter(in_stream.readline, b""):
        try:
            messages = buf.feed(line)
        except FramingError:
            continue
        for msg in messages:
            reply = server.handle_message(msg)
            if reply is not None:
                out_stream.write(encode_message(reply))
                out_stream.flush()
                replies += 1
    return replies
