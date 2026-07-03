"""Webhook alert — make drift loud (M14). Stdlib only; Slack-compatible payload.

The exit code (3) is the primary alert; this is the optional loud path: POST the drift report
to any webhook URL (Slack incoming webhooks read the ``text`` field; everything else gets the
full report under ``volo``).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from volo_shadow.drift import DriftReport


def webhook_payload(drift: DriftReport, *, agent: str | None = None) -> dict[str, Any]:
    worst = min(drift.findings, key=lambda f: f.delta, default=None)
    headline = f"Volo drift sentinel: {len(drift.findings)} finding(s)"
    if agent:
        headline += f" for {agent}"
    if worst is not None:
        headline += (
            f" — worst: {worst.dimension} {worst.baseline:.3f} -> {worst.current:.3f}"
            f" on {worst.run_id}"
        )
    return {"text": headline, "volo": drift.to_dict()}


def post_webhook(url: str, payload: dict[str, Any], *, timeout_s: float = 10.0) -> int:
    """POST JSON to the webhook; return the HTTP status. Raises on network failure."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return int(resp.status)
