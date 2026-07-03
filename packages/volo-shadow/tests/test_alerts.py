"""Webhook alert: Slack-compatible payload, delivered over real HTTP."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from volo_shadow import DriftFinding, DriftReport, post_webhook, webhook_payload


def _drift() -> DriftReport:
    report = DriftReport(threshold=0.05)
    report.findings.append(
        DriftFinding(run_id="r1", dimension="decision_determinism", baseline=1.0, current=0.5)
    )
    return report


def test_payload_is_slack_compatible_and_carries_the_report() -> None:
    payload = webhook_payload(_drift(), agent="checkout:run")
    assert "1 finding(s)" in payload["text"]
    assert "checkout:run" in payload["text"]
    assert "decision_determinism 1.000 -> 0.500" in payload["text"]
    assert payload["volo"]["drifted"] is True


def test_post_webhook_delivers_json() -> None:
    received: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            received.append(json.loads(body))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: Any) -> None:  # keep test output quiet
            del args

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/hook"
        status = post_webhook(url, webhook_payload(_drift()))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert received and received[0]["volo"]["findings"][0]["run_id"] == "r1"
