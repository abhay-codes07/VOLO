"""Cloud control plane: team → workspace → API key → ingest/list reports, scoped + authed."""

from __future__ import annotations

from pathlib import Path

import pytest
import volo_cloud.app as cloud_app
from fastapi.testclient import TestClient
from volo_cloud import service

from volo_core.storage import get_engine, init_schema


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'cloud.db').as_posix()}")
    monkeypatch.setattr(cloud_app, "_engine", None)  # reset the cached engine per test
    return TestClient(cloud_app.create_cloud_app())


def _engine(tmp_path: Path):
    eng = get_engine()
    init_schema(eng)
    return eng


def test_healthz(client: TestClient) -> None:
    assert client.get("/cloud/healthz").json()["plane"] == "cloud"


def test_full_flow_team_workspace_key_reports(client: TestClient) -> None:
    team = client.post("/cloud/teams", json={"slug": "acme", "name": "Acme"}).json()
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "prod", "name": "Prod"}
    ).json()
    key_resp = client.post(f"/cloud/workspaces/{ws['id']}/keys", json={"name": "ci"}).json()
    assert key_resp["key"].startswith("volo_sk_")
    key = key_resp["key"]

    headers = {"X-Volo-Key": key}
    # ingest a report
    ing = client.post(
        f"/cloud/workspaces/{ws['id']}/reports",
        json={
            "baseline_run_id": "run-1",
            "agent_name": "bot",
            "verdict": "ship",
            "aggregate": {"faithfulness": 1.0},
            "n_scenarios": 7,
        },
        headers=headers,
    )
    assert ing.status_code == 200, ing.text

    rows = client.get(f"/cloud/workspaces/{ws['id']}/reports", headers=headers).json()
    assert len(rows) == 1 and rows[0]["verdict"] == "ship" and rows[0]["n_scenarios"] == 7


def test_reports_require_api_key(client: TestClient) -> None:
    team = client.post("/cloud/teams", json={"slug": "t", "name": "T"}).json()
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "w", "name": "W"}
    ).json()
    # no key → 401
    assert client.get(f"/cloud/workspaces/{ws['id']}/reports").status_code == 401
    # bad key → 401
    r = client.get(f"/cloud/workspaces/{ws['id']}/reports", headers={"X-Volo-Key": "nope"})
    assert r.status_code == 401


def test_key_scoped_to_its_workspace(client: TestClient) -> None:
    team = client.post("/cloud/teams", json={"slug": "t", "name": "T"}).json()
    ws1 = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "w1", "name": "W1"}
    ).json()
    ws2 = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "w2", "name": "W2"}
    ).json()
    key = client.post(f"/cloud/workspaces/{ws1['id']}/keys", json={"name": "k"}).json()["key"]
    # ws1 key cannot read ws2
    r = client.get(f"/cloud/workspaces/{ws2['id']}/reports", headers={"X-Volo-Key": key})
    assert r.status_code == 403


def test_duplicate_team_slug_conflicts(client: TestClient) -> None:
    assert client.post("/cloud/teams", json={"slug": "dup", "name": "A"}).status_code == 200
    assert client.post("/cloud/teams", json={"slug": "dup", "name": "B"}).status_code == 409


def test_require_auth_denies_anonymous_management(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    monkeypatch.setattr(cloud_app, "_engine", None)
    client = TestClient(cloud_app.create_cloud_app())
    # anonymous management is denied when auth is required (the vendor swap point)
    assert client.post("/cloud/teams", json={"slug": "x", "name": "X"}).status_code == 401


def test_service_key_hashing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 's.db').as_posix()}")
    eng = _engine(tmp_path)
    team = service.create_team(eng, slug="t", name="T")
    ws = service.create_workspace(eng, team_id=team.id, slug="w", name="W")
    row, plaintext = service.mint_api_key(eng, workspace_id=ws.id, name="k")
    # the plaintext is never stored; only its hash
    assert row.key_hash != plaintext
    assert service.resolve_api_key(eng, plaintext).id == row.id
    assert service.resolve_api_key(eng, "wrong") is None
    # revocation
    assert service.revoke_api_key(eng, row.id) is True
    assert service.resolve_api_key(eng, plaintext) is None
