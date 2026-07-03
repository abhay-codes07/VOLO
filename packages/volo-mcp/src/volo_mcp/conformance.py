"""Conformance — replay a recording's requests against the LIVE server and diff (M11).

The regression harness for MCP-server *authors*: a recording is a behavioral contract, and this
module checks whether the current server build still honors it. Every recorded request is sent
to a freshly spawned server; each live reply is compared against the recorded envelope.

Verdicts per step: ``identical`` (byte-equal result/error), ``different`` (server behavior
changed), ``no_reply`` (server never answered). Any non-identical verdict fails the report.

Caveat: requests are rebuilt from the recorded cache identity (``messages.request_message``),
which drops ``tools/call`` params beyond ``name``/``arguments`` — servers that key behavior on
exotic params may need a fresh recording instead.
"""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Literal, cast

from volo_core import Recording
from volo_mcp.framing import FramingError, MessageBuffer, encode_message
from volo_mcp.messages import envelope, is_response, request_message

Verdict = Literal["identical", "different", "no_reply"]


@dataclass(frozen=True)
class StepVerdict:
    index: int
    tool: str
    verdict: Verdict


@dataclass
class ConformanceReport:
    server_cmd: list[str]
    verdicts: list[StepVerdict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(v.verdict == "identical" for v in self.verdicts)

    def counts(self) -> dict[str, int]:
        out = {"identical": 0, "different": 0, "no_reply": 0}
        for v in self.verdicts:
            out[v.verdict] += 1
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_cmd": self.server_cmd,
            "passed": self.passed,
            "counts": self.counts(),
            "steps": [
                {"index": v.index, "tool": v.tool, "verdict": v.verdict} for v in self.verdicts
            ],
        }


def check_conformance(
    recording: Recording,
    server_cmd: list[str],
    *,
    timeout_s: float = 15.0,
) -> ConformanceReport:
    """Spawn ``server_cmd``, replay every recorded request, and diff the live replies."""
    # (step index, tool, recorded response) — the step index doubles as the JSON-RPC id
    requests: list[tuple[int, str, dict[str, Any]]] = []
    wire: list[bytes] = []
    for i, step in enumerate(recording.steps):
        if step.payload.type != "tool_call" or step.payload.response is None:
            continue
        requests.append((i, step.payload.tool, step.payload.response))
        wire.append(encode_message(request_message(i, step.payload.tool, step.payload.request)))

    report = ConformanceReport(server_cmd=list(server_cmd))
    if not requests:
        return report

    proc = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        bufsize=0,
    )
    assert proc.stdin is not None and proc.stdout is not None

    replies: dict[int, dict[str, Any]] = {}
    reader = threading.Thread(target=_collect_replies, args=(proc.stdout, replies), daemon=True)
    reader.start()
    try:
        for chunk in wire:
            proc.stdin.write(chunk)
            proc.stdin.flush()
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        reader.join(timeout=timeout_s)

    for i, tool, recorded in requests:
        reply = replies.get(i)
        if reply is None:
            verdict: Verdict = "no_reply"
        elif envelope(reply) == recorded:
            verdict = "identical"
        else:
            verdict = "different"
        report.verdicts.append(StepVerdict(index=i, tool=tool, verdict=verdict))
    return report


def _collect_replies(server_out: BinaryIO, replies: dict[int, dict[str, Any]]) -> None:
    buf = MessageBuffer()
    for line in iter(server_out.readline, b""):
        try:
            messages = buf.feed(line)
        except FramingError:
            continue
        for msg in messages:
            if is_response(msg) and isinstance(msg.get("id"), int):
                replies[cast(int, msg["id"])] = msg
