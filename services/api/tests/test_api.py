"""FastAPI integration tests using TestClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from volo_api import create_app
from volo_core import ModelCallPayload, Recording


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    (tmp_path / "recordings").mkdir()
    (tmp_path / "reports").mkdir()
    # Seed one recording.
    r = Recording()
    r.add_step(ModelCallPayload(provider="p", model="m", request={"q": 1}, response={"a": 2}))
    (tmp_path / "recordings" / f"{r.run_id}.json").write_text(r.to_json(), encoding="utf-8")
    return TestClient(create_app())


def test_healthz(client: TestClient) -> None:
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert "db" in body


def test_list_recordings_returns_seeded(client: TestClient) -> None:
    rows = client.get("/recordings").json()
    assert len(rows) == 1
    assert rows[0]["n_steps"] == 1


def test_get_recording_returns_full_recording(client: TestClient) -> None:
    rows = client.get("/recordings").json()
    run_id = rows[0]["run_id"]
    full = client.get(f"/recordings/{run_id}").json()
    assert full["recording_schema_version"] == "1.0.0"
    assert len(full["steps"]) == 1


def test_get_recording_404_for_unknown(client: TestClient) -> None:
    res = client.get("/recordings/does-not-exist")
    assert res.status_code == 404


def test_list_reports_empty_when_dir_empty(client: TestClient) -> None:
    assert client.get("/reports").json() == []


def test_diff_post_returns_diff(client: TestClient, tmp_path: Path) -> None:
    # Drop a second recording — identical to the first — and diff them.
    rows = client.get("/recordings").json()
    a_id = rows[0]["run_id"]
    src = (tmp_path / "recordings" / f"{a_id}.json").read_text(encoding="utf-8")
    r = Recording.from_json(src)
    # Mutate just the response so we expect a diff.
    r.steps[0].payload.response = {"a": 999}
    new = r.model_copy(update={"run_id": "cand-001"})
    (tmp_path / "recordings" / "cand-001.json").write_text(new.to_json(), encoding="utf-8")

    res = client.post("/diff", json={"baseline_id": a_id, "candidate_id": "cand-001"})
    assert res.status_code == 200
    body = res.json()
    assert body["first_diverging_step"] is not None
