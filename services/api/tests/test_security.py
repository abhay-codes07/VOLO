"""Security regression tests for the API (M9 review, ADR-0012).

Covers the path-traversal containment guard and the opt-in auth enforcement. All offline —
no network, no live API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from volo_api import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    for sub in ("recordings", "reports", "diffs"):
        (tmp_path / sub).mkdir()
    (tmp_path / "diffs" / "ok.json").write_text(json.dumps({"diff": "fine"}), encoding="utf-8")
    # A secret file OUTSIDE the data dir that traversal must not reach.
    (tmp_path.parent / "SECRET_PROBE.json").write_text(
        json.dumps({"leaked": True}),
        encoding="utf-8",
    )
    return TestClient(create_app())


# ── path traversal (CWE-22) ──────────────────────────────────────────────────


def test_diff_stem_happy_path(client: TestClient) -> None:
    assert client.get("/diffs/ok").json() == {"diff": "fine"}


@pytest.mark.parametrize(
    "evil",
    [
        "..%2F..%2FSECRET_PROBE",  # encoded forward-slash traversal
        "..%5C..%5CSECRET_PROBE",  # encoded backslash traversal (Windows)
        "....%2F....%2FSECRET_PROBE",
    ],
)
def test_diff_stem_traversal_is_blocked(client: TestClient, evil: str) -> None:
    res = client.get(f"/diffs/{evil}")
    # Either rejected (404) or simply not found — never a 200 leaking the outside file.
    assert res.status_code == 404
    assert "leaked" not in res.text


def test_recording_id_traversal_is_blocked(client: TestClient) -> None:
    res = client.get("/recordings/..%5C..%5CSECRET_PROBE")
    assert res.status_code == 404
    assert "leaked" not in res.text


# ── auth enforcement (opt-in) ────────────────────────────────────────────────


def test_mutating_route_open_in_oss_default(client: TestClient) -> None:
    # Default OSS posture: VOLO_REQUIRE_AUTH unset → anonymous POST allowed.
    res = client.post("/projects", json={"slug": "p1", "name": "P1"})
    assert res.status_code in (200, 201)


def test_mutating_route_401_when_auth_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    c = TestClient(create_app())
    res = c.post("/projects", json={"slug": "p1", "name": "P1"})
    assert res.status_code == 401


def test_read_routes_unaffected_by_auth_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    (tmp_path / "recordings").mkdir()
    c = TestClient(create_app())
    assert c.get("/healthz").status_code == 200
