"""Storage layer tests — SQLite + Project / AgentVersion / RecordingRow / ReportRow."""

from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import select

from volo_core import ModelCallPayload, Recording, ToolCallPayload
from volo_core.storage import (
    AgentVersion,
    Project,
    RecordingRow,
    get_engine,
    init_schema,
    list_recordings,
    list_reports,
    session,
    store_recording,
    store_report,
)


def _make_recording() -> Recording:
    r = Recording()
    r.add_step(ModelCallPayload(provider="ollama", model="llama3.2:3b", request={"p": "hi"}))
    r.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": []}))
    r.final_output = {"answer": 1}
    return r


def test_sqlite_default_creates_db_under_data_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOLO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("VOLO_DB_URL", raising=False)
    engine = get_engine()
    init_schema(engine)
    assert (tmp_path / "volo.db").exists()


def test_explicit_url_wins(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'override.db').as_posix()}")
    engine = get_engine()
    init_schema(engine)
    assert (tmp_path / "override.db").exists()


def test_project_and_agent_version(tmp_path: Path) -> None:
    engine = get_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    init_schema(engine)
    with session(engine) as s:
        proj = Project(slug="research", name="Research Agent")
        s.add(proj)
        s.commit()
        s.refresh(proj)
        av = AgentVersion(project_id=proj.id, commit="abc123", framework="raw", label="v0.1")
        s.add(av)
        s.commit()
        s.refresh(av)
        assert av.project_id == proj.id


def test_store_recording_upsert(tmp_path: Path) -> None:
    engine = get_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    init_schema(engine)
    rec = _make_recording()
    row1 = store_recording(engine, rec, path="/x/calc.json", stem="calc")
    # Second call with same run_id should update, not duplicate.
    rec.final_output = {"answer": 99}
    row2 = store_recording(engine, rec, path="/x/calc.json", stem="calc")
    assert row1.id == row2.id
    with session(engine) as s:
        rows = list(s.exec(select(RecordingRow)))
        assert len(rows) == 1
        assert json.loads(rows[0].final_output_json) == {"answer": 99}


def test_store_report_round_trip(tmp_path: Path) -> None:
    from volo_reliability import aggregate_runs, compose_report

    engine = get_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    init_schema(engine)
    runs = [_make_recording()]
    sub = aggregate_runs(runs, scenario_op="x", failure_class="y", seed=0)
    rep = compose_report(runs[0], [sub])
    row = store_report(engine, rep, path="/x/r.json", stem="r")
    assert row.baseline_run_id == rep.baseline_run_id
    assert row.verdict in ("ship", "no_ship")


def test_list_helpers(tmp_path: Path) -> None:
    engine = get_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    init_schema(engine)
    assert list_recordings(engine) == []
    assert list_reports(engine) == []
    store_recording(engine, _make_recording(), path="/x.json", stem="x")
    assert len(list_recordings(engine)) == 1
