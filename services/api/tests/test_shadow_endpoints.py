"""GET /shadow/history — the drift-sentinel trend feed for the dashboard (M14)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from volo_api import create_app
from volo_core import Recording, ToolCallPayload
from volo_shadow import CorpusBank, DriftFinding, DriftReport, SnapshotHistory


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))

    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 1}))
    bank = CorpusBank(tmp_path / "corpus")
    entry = bank.add(rec, source="incident")
    assert entry is not None

    history = SnapshotHistory(tmp_path / "shadow-history.jsonl")
    snap = {
        "snapshot_version": 1,
        "entries": {entry.run_id: {"aggregate": {"decision_determinism": 1.0}, "verdict": "ship"}},
    }
    history.append(snap, at="2026-07-03T03:17:00+00:00")
    drift = DriftReport(threshold=0.05)
    drift.findings.append(
        DriftFinding(
            run_id=entry.run_id, dimension="decision_determinism", baseline=1.0, current=0.5
        )
    )
    bad = {
        "snapshot_version": 1,
        "entries": {entry.run_id: {"aggregate": {"decision_determinism": 0.5}, "verdict": "ship"}},
    }
    history.append(bad, drift=drift, at="2026-07-04T03:17:00+00:00")

    return TestClient(create_app())


def test_shadow_history_returns_checks_and_corpus(client: TestClient) -> None:
    body = client.get("/shadow/history").json()
    assert len(body["checks"]) == 2
    assert body["checks"][0]["drifted"] is False
    assert body["checks"][1]["drifted"] is True and body["checks"][1]["findings"] == 1
    assert body["checks"][1]["aggregate"]["decision_determinism"] == 0.5
    assert len(body["corpus"]) == 1 and body["corpus"][0]["source"] == "incident"


def test_shadow_trace_history(client: TestClient) -> None:
    run_id = client.get("/shadow/history").json()["corpus"][0]["run_id"]
    body = client.get(f"/shadow/history/{run_id}").json()
    assert [p["aggregate"]["decision_determinism"] for p in body["checks"]] == [1.0, 0.5]

    assert client.get("/shadow/history/unknown-run").status_code == 404


def test_shadow_history_empty_is_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path / "empty"))
    client = TestClient(create_app())
    body = client.get("/shadow/history").json()
    assert body == {"checks": [], "corpus": []}
