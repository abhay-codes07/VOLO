"""Hosted sim-minutes: enqueue → worker runs → meters → charges quota; hard cap + agent gating."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import volo_cloud.app as cloud_app
from fastapi.testclient import TestClient
from volo_cloud import service, sim_service
from volo_cloud.worker import run_next_job

from volo_core import current_recorder
from volo_core.storage import get_engine, init_schema
from volo_sdk import Recorder, RecorderConfig

CALC = "examples.calc_agent:run"
CALC_INPUT = {"a": 2, "b": 3, "c": 4}


def _recording_json() -> dict[str, Any]:
    from examples.calc_agent import run as calc

    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        rec.set_final_output(calc(CALC_INPUT))
    return rec.recording.model_dump(mode="json", by_alias=True)


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    monkeypatch.setattr(cloud_app, "_engine", None)
    eng = get_engine()
    init_schema(eng)
    return eng


def _workspace(engine) -> int:
    team = service.create_team(engine, slug="t", name="T")
    ws = service.create_workspace(engine, team_id=team.id, slug="w", name="W")
    return ws.id


def test_worker_runs_job_meters_and_charges_quota(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_SIM_AGENT_ALLOWLIST", CALC)
    ws_id = _workspace(engine)
    sim_service.set_quota(engine, workspace_id=ws_id, minutes=10)

    job = sim_service.enqueue_job(
        engine, workspace_id=ws_id, agent=CALC, agent_input=CALC_INPUT, recording=_recording_json()
    )
    assert job.status == "queued"

    done = run_next_job(engine, duration_s=90.0)  # 90s -> 2 sim-minutes
    assert done.status == "done"
    assert done.sim_minutes == 2
    assert done.result_verdict in ("ship", "no_ship")

    quota = sim_service.get_or_create_quota(engine, workspace_id=ws_id)
    assert quota.sim_minutes_used == 2 and quota.remaining == 8
    # the report landed in the workspace history (M26)
    assert len(service.list_reports(engine, workspace_id=ws_id)) == 1


def test_quota_hard_cap_blocks_enqueue(engine) -> None:
    ws_id = _workspace(engine)
    sim_service.set_quota(engine, workspace_id=ws_id, minutes=0)
    with pytest.raises(sim_service.QuotaExceeded):
        sim_service.enqueue_job(
            engine, workspace_id=ws_id, agent=CALC, agent_input={}, recording={"run_id": "r"}
        )


def test_disallowed_agent_fails_job_without_executing(
    engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VOLO_SIM_AGENT_ALLOWLIST", raising=False)
    monkeypatch.delenv("VOLO_SIM_TRUST_AGENTS", raising=False)
    ws_id = _workspace(engine)
    sim_service.enqueue_job(
        engine,
        workspace_id=ws_id,
        agent="evil.module:pwn",
        agent_input={},
        recording={"run_id": "r"},
    )
    done = run_next_job(engine, duration_s=1.0)
    assert done.status == "failed" and "not allowlisted" in done.error
    # a failed (rejected) job is not charged
    assert sim_service.get_or_create_quota(engine, workspace_id=ws_id).sim_minutes_used == 0


def test_empty_queue_returns_none(engine) -> None:
    assert run_next_job(engine) is None


def test_end_to_end_over_api(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_SIM_AGENT_ALLOWLIST", CALC)
    client = TestClient(cloud_app.create_cloud_app())
    team = client.post("/cloud/teams", json={"slug": "a", "name": "A"}).json()
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "p", "name": "P"}
    ).json()
    key = client.post(f"/cloud/workspaces/{ws['id']}/keys", json={"name": "k"}).json()["key"]
    h = {"X-Volo-Key": key}

    enq = client.post(
        f"/cloud/workspaces/{ws['id']}/sim-jobs",
        json={"agent": CALC, "agent_input": CALC_INPUT, "recording": _recording_json()},
        headers=h,
    )
    assert enq.status_code == 200, enq.text
    job_id = enq.json()["id"]

    run_next_job(engine, duration_s=30.0)  # 30s -> 1 sim-minute

    job = client.get(f"/cloud/workspaces/{ws['id']}/sim-jobs/{job_id}", headers=h).json()
    assert job["status"] == "done" and job["sim_minutes"] == 1
    quota = client.get(f"/cloud/workspaces/{ws['id']}/quota", headers=h).json()
    assert quota["sim_minutes_used"] == 1


def test_enqueue_over_api_402_when_exhausted(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(cloud_app.create_cloud_app())
    team = client.post("/cloud/teams", json={"slug": "a", "name": "A"}).json()
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "p", "name": "P"}
    ).json()
    key = client.post(f"/cloud/workspaces/{ws['id']}/keys", json={"name": "k"}).json()["key"]
    h = {"X-Volo-Key": key}
    client.put(f"/cloud/workspaces/{ws['id']}/quota", json={"minutes": 0})

    r = client.post(
        f"/cloud/workspaces/{ws['id']}/sim-jobs",
        json={"agent": CALC, "agent_input": {}, "recording": {"run_id": "r"}},
        headers=h,
    )
    assert r.status_code == 402 and "no sim-minutes" in r.json()["detail"]
