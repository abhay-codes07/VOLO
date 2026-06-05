"""Tests for SSE streaming + DB-backed project / agent-version routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from volo_api import create_app
from volo_core import ModelCallPayload, Recording, ToolCallPayload


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'volo.db').as_posix()}")
    (tmp_path / "recordings").mkdir()
    (tmp_path / "reports").mkdir()
    # Reset module-level engine cache.
    import volo_api.main as _m

    _m._engine = None
    return TestClient(create_app())


def test_healthz_reports_db_active(client: TestClient) -> None:
    body = client.get("/healthz").json()
    assert body == {"status": "ok", "db": True}


def test_projects_round_trip(client: TestClient) -> None:
    created = client.post("/projects", json={"slug": "x", "name": "X"}).json()
    assert created["slug"] == "x"
    listed = client.get("/projects").json()
    assert len(listed) == 1


def test_agent_version_created(client: TestClient) -> None:
    proj = client.post("/projects", json={"slug": "y", "name": "Y"}).json()
    av = client.post(
        "/agent-versions",
        json={
            "project_id": proj["id"],
            "commit": "abc",
            "framework": "raw",
            "label": "v1",
        },
    ).json()
    assert av["commit"] == "abc"
    assert av["project_id"] == proj["id"]


def test_stream_run_replays_steps_as_sse_events(client: TestClient, tmp_path: Path) -> None:
    r = Recording()
    r.add_step(ModelCallPayload(provider="p", model="m", request={}, response={"x": 1}))
    r.add_step(ToolCallPayload(tool="t", request={}, response={"y": 2}))
    (tmp_path / "recordings" / f"{r.run_id}.json").write_text(r.to_json(), encoding="utf-8")

    res = client.get(f"/runs/{r.run_id}/stream")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    body = res.text
    assert "event: start" in body
    assert body.count("event: step") == 2
    assert "event: done" in body


def test_stream_run_404_for_unknown(client: TestClient) -> None:
    assert client.get("/runs/nope/stream").status_code == 404


def test_ci_reports_endpoint_present(client: TestClient) -> None:
    # Empty initially.
    assert client.get("/ci/reports").json() == []
