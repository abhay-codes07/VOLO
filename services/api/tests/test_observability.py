"""Tests for the logging + request-timing observability seam."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from volo_api import create_app
from volo_api.observability import log_level


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    return TestClient(create_app())


class _CaptureHandler(logging.Handler):
    """Collects emitted records without depending on caplog/basicConfig interplay."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_healthz_is_unauthenticated_even_when_auth_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_request_id_is_generated_and_echoed(client: TestClient) -> None:
    resp = client.get("/healthz")
    rid = resp.headers.get("X-Request-ID")
    assert rid and len(rid) >= 8


def test_inbound_request_id_is_propagated(client: TestClient) -> None:
    resp = client.get("/healthz", headers={"X-Request-ID": "trace-abc-123"})
    assert resp.headers["X-Request-ID"] == "trace-abc-123"


def test_request_is_logged_with_structured_fields(client: TestClient) -> None:
    handler = _CaptureHandler()
    logger = logging.getLogger("volo.api")
    logger.addHandler(handler)
    try:
        client.get("/healthz")
    finally:
        logger.removeHandler(handler)

    req_logs = [r for r in handler.records if r.getMessage() == "request"]
    assert req_logs, "expected a 'request' log line"
    fields = req_logs[-1].__dict__["fields"]
    assert fields["method"] == "GET"
    assert fields["path"] == "/healthz"
    assert fields["status"] == 200
    assert "dur_ms" in fields
    assert "request_id" in fields


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("debug", logging.DEBUG),
        ("WARNING", logging.WARNING),
        ("", logging.INFO),
        ("nonsense", logging.INFO),
    ],
)
def test_log_level_resolution(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    monkeypatch.setenv("VOLO_LOG_LEVEL", value)
    assert log_level() == expected
