"""FastAPI app factory + routes (bible §9.6).

Resolution order for every read:

1. **Database** when ``VOLO_DB_URL`` is set or the SQLite file at ``./.volo/volo.db``
   already exists. New routes ``/projects``, ``/agent-versions``, ``/ci/reports`` are
   DB-only.
2. **Filesystem** under ``VOLO_DATA_DIR`` (default ``./.volo``) — the bootstrap path.

All routes carry a ``Depends(get_principal)`` so cloud can swap in real auth without
touching the route bodies.
"""

from __future__ import annotations

import json as _json
import os
from pathlib import Path
from typing import Any, cast

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from volo_api.auth import Principal, get_principal, require_principal
from volo_api.streaming import stream_recording
from volo_core import Recording
from volo_core.env import load_env
from volo_core.storage import (
    AgentVersion,
    Project,
    get_engine,
    init_schema,
    session,
)
from volo_core.storage import (
    list_recordings as db_list_recordings,
)
from volo_core.storage import (
    list_reports as db_list_reports,
)
from volo_diff import compute_diff
from volo_reliability import ReliabilityReport
from volo_scenarios import default_library

# ── storage strategy ────────────────────────────────────────────────────────


def _data_dir() -> Path:
    return Path(os.environ.get("VOLO_DATA_DIR", "./.volo"))


def _db_active() -> bool:
    if os.environ.get("VOLO_DB_URL"):
        return True
    return (_data_dir() / "volo.db").exists()


_engine = None


def _get_engine_cached() -> Any:
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_schema(_engine)
    return _engine


# ── filesystem path lookups ─────────────────────────────────────────────────


def _safe_data_path(subdir: str, name: str) -> Path | None:
    """Resolve ``<data_dir>/<subdir>/<name>.json``, or ``None`` if ``name`` is unsafe.

    Defends against path traversal (CWE-22): rejects path separators (``/`` and ``\\``),
    ``..``, drive/colon markers, null bytes, and absolute paths, then verifies the *resolved*
    path is still contained within the subdir (catches symlink/encoding escapes). ``run_id``s
    and diff stems never legitimately contain these characters.
    """
    if not name or name in (".", ".."):
        return None
    if ".." in name or any(c in name for c in ("\x00", "/", "\\", ":")):
        return None
    if Path(name).is_absolute():
        return None
    base = (_data_dir() / subdir).resolve()
    candidate = (base / f"{name}.json").resolve()
    if base not in candidate.parents:
        return None
    return candidate


def _max_artifact_bytes() -> int:
    """Per-artifact read cap (DoS guard). Override with ``VOLO_MAX_ARTIFACT_BYTES``."""
    try:
        return int(os.environ.get("VOLO_MAX_ARTIFACT_BYTES", str(32 * 1024 * 1024)))
    except ValueError:
        return 32 * 1024 * 1024


def _read_capped(path: Path) -> str:
    """Read a JSON artifact, refusing files larger than the cap (avoids memory-exhaustion)."""
    if path.stat().st_size > _max_artifact_bytes():
        raise HTTPException(status_code=413, detail="artifact too large")
    return path.read_text(encoding="utf-8")


def _recording_path(run_id: str) -> Path | None:
    rec_dir = _data_dir() / "recordings"
    if not rec_dir.exists():
        return None
    direct = _safe_data_path("recordings", run_id)
    if direct is not None and direct.exists():
        return direct
    for path in rec_dir.glob("*.json"):
        if path.stem == run_id:
            return path
        try:
            rec = Recording.from_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.run_id == run_id:
            return path
    return None


def _report_path(run_id: str) -> Path | None:
    rep_dir = _data_dir() / "reports"
    if not rep_dir.exists():
        return None
    direct = _safe_data_path("reports", run_id)
    if direct is not None and direct.exists():
        return direct
    for path in rep_dir.glob("*.json"):
        if path.stem == run_id:
            return path
        try:
            rep = ReliabilityReport.from_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rep.baseline_run_id == run_id:
            return path
    return None


# ── models ──────────────────────────────────────────────────────────────────


class DiffRequest(BaseModel):
    baseline_id: str
    candidate_id: str


class ProjectIn(BaseModel):
    slug: str
    name: str


class AgentVersionIn(BaseModel):
    project_id: int
    commit: str
    framework: str = "raw"
    label: str | None = None


# ── factory ─────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    load_env()  # pick up a local .env before the app reads any VOLO_* / DB config
    app = FastAPI(
        title="Volo",
        version="0.1.0",
        description="Read-only API over local Volo recordings + reliability reports.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz(principal: Principal = Depends(get_principal)) -> dict[str, Any]:
        del principal  # auth seam only — no body use yet
        return {"status": "ok", "db": _db_active()}

    @app.get("/recordings")
    def list_recordings(
        principal: Principal = Depends(get_principal),
    ) -> list[dict[str, Any]]:
        del principal
        if _db_active():
            engine = _get_engine_cached()
            rows = db_list_recordings(engine)
            if rows:
                return [
                    {
                        "run_id": r.run_id,
                        "stem": r.stem,
                        "created_at": r.created_at.isoformat(),
                        "agent_name": None,
                        "framework": "raw",
                        "n_steps": r.n_steps,
                        "redaction_applied": r.redaction_applied,
                        "final_output": _json.loads(r.final_output_json or "null"),
                    }
                    for r in rows
                ]
        rec_dir = _data_dir() / "recordings"
        if not rec_dir.exists():
            return []
        out: list[dict[str, Any]] = []
        for path in sorted(rec_dir.glob("*.json")):
            try:
                rec = Recording.from_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append(
                {
                    "run_id": rec.run_id,
                    "stem": path.stem,
                    "created_at": rec.created_at,
                    "agent_name": rec.agent_meta.agent_name,
                    "framework": rec.agent_meta.framework,
                    "n_steps": len(rec.steps),
                    "redaction_applied": rec.redaction_applied,
                    "final_output": rec.final_output,
                }
            )
        return out

    @app.get("/recordings/{run_id}")
    def get_recording(
        run_id: str,
        principal: Principal = Depends(get_principal),
    ) -> dict[str, Any]:
        del principal
        path = _recording_path(run_id)
        if path is None:
            raise HTTPException(status_code=404, detail=f"recording {run_id!r} not found")
        rec = Recording.from_json(_read_capped(path))
        return rec.model_dump(mode="python", by_alias=True)

    # ── SSE stream ─────────────────────────────────────────────────────────

    @app.get("/runs/{run_id}/stream")
    async def stream_run(
        run_id: str,
        principal: Principal = Depends(get_principal),
    ) -> StreamingResponse:
        del principal
        path = _recording_path(run_id)
        if path is None:
            raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
        rec = Recording.from_json(_read_capped(path))
        return StreamingResponse(
            stream_recording(rec),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/reports")
    def list_reports(
        principal: Principal = Depends(get_principal),
    ) -> list[dict[str, Any]]:
        del principal
        if _db_active():
            engine = _get_engine_cached()
            rows = db_list_reports(engine)
            if rows:
                return [
                    {
                        "baseline_run_id": r.baseline_run_id,
                        "stem": r.stem,
                        "agent_name": r.agent_name,
                        "verdict": r.verdict,
                        "aggregate": _json.loads(r.aggregate_json or "{}"),
                        "n_scenarios": r.n_scenarios,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in rows
                ]
        rep_dir = _data_dir() / "reports"
        if not rep_dir.exists():
            return []
        out: list[dict[str, Any]] = []
        for path in sorted(rep_dir.glob("*.json")):
            try:
                rep = ReliabilityReport.from_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append(
                {
                    "baseline_run_id": rep.baseline_run_id,
                    "stem": path.stem,
                    "agent_name": rep.agent_name,
                    "verdict": rep.verdict,
                    "aggregate": rep.aggregate,
                    "n_scenarios": len(rep.scenarios),
                }
            )
        return out

    @app.get("/reports/{run_id}")
    def get_report(
        run_id: str,
        principal: Principal = Depends(get_principal),
    ) -> dict[str, Any]:
        del principal
        path = _report_path(run_id)
        if path is None:
            raise HTTPException(status_code=404, detail=f"report {run_id!r} not found")
        return ReliabilityReport.from_json(path.read_text(encoding="utf-8")).model_dump(
            mode="python"
        )

    @app.get("/ci/reports")
    def list_ci_reports(
        principal: Principal = Depends(get_principal),
    ) -> list[dict[str, Any]]:
        del principal
        if _db_active():
            engine = _get_engine_cached()
            rows = db_list_reports(engine)
            return [
                {
                    "baseline_run_id": r.baseline_run_id,
                    "stem": r.stem,
                    "agent_name": r.agent_name,
                    "verdict": r.verdict,
                    "aggregate": _json.loads(r.aggregate_json or "{}"),
                    "n_scenarios": r.n_scenarios,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        rep_dir = _data_dir() / "reports"
        if not rep_dir.exists():
            return []
        entries: list[tuple[float, dict[str, Any]]] = []
        for path in rep_dir.glob("*.json"):
            try:
                rep = ReliabilityReport.from_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            mtime = path.stat().st_mtime
            entries.append(
                (
                    mtime,
                    {
                        "baseline_run_id": rep.baseline_run_id,
                        "stem": path.stem,
                        "agent_name": rep.agent_name,
                        "verdict": rep.verdict,
                        "aggregate": rep.aggregate,
                        "n_scenarios": len(rep.scenarios),
                        "created_at": str(mtime),
                    },
                )
            )
        entries.sort(key=lambda e: e[0])
        return [e[1] for e in entries]

    @app.get("/scenarios")
    def list_scenarios(
        principal: Principal = Depends(get_principal),
    ) -> list[dict[str, Any]]:
        del principal
        out: list[dict[str, Any]] = []
        for op in default_library(seed=0):
            doc = (
                (op.__class__.__doc__ or "").strip().splitlines()[0] if op.__class__.__doc__ else ""
            )
            out.append(
                {
                    "name": op.name,
                    "failure_class": op.failure_class,
                    "description": doc,
                }
            )
        return out

    @app.get("/diffs/{stem}")
    def get_diff(
        stem: str,
        principal: Principal = Depends(get_principal),
    ) -> dict[str, Any]:
        del principal
        path = _safe_data_path("diffs", stem)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail=f"diff {stem!r} not found")
        return cast("dict[str, Any]", _json.loads(_read_capped(path)))

    @app.post("/diff")
    def post_diff(
        body: DiffRequest,
        principal: Principal = Depends(get_principal),
    ) -> dict[str, Any]:
        del principal
        a_path = _recording_path(body.baseline_id)
        b_path = _recording_path(body.candidate_id)
        if a_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"recording {body.baseline_id!r} not found",
            )
        if b_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"recording {body.candidate_id!r} not found",
            )
        a = Recording.from_json(_read_capped(a_path))
        b = Recording.from_json(_read_capped(b_path))
        return compute_diff(a, b).model_dump(mode="python")

    @app.get("/projects")
    def list_projects(
        principal: Principal = Depends(get_principal),
    ) -> list[dict[str, Any]]:
        del principal
        if not _db_active():
            return []
        engine = _get_engine_cached()
        from sqlmodel import select as _select

        with session(engine) as s:
            return [
                {"id": p.id, "slug": p.slug, "name": p.name, "created_at": p.created_at.isoformat()}
                for p in s.exec(_select(Project))
            ]

    @app.post("/projects")
    def create_project(
        body: ProjectIn,
        principal: Principal = Depends(require_principal),
    ) -> dict[str, Any]:
        del principal
        engine = _get_engine_cached()
        with session(engine) as s:
            p = Project(slug=body.slug, name=body.name)
            s.add(p)
            s.commit()
            s.refresh(p)
            return {
                "id": p.id,
                "slug": p.slug,
                "name": p.name,
                "created_at": p.created_at.isoformat(),
            }

    @app.post("/agent-versions")
    def create_agent_version(
        body: AgentVersionIn,
        principal: Principal = Depends(require_principal),
    ) -> dict[str, Any]:
        del principal
        engine = _get_engine_cached()
        with session(engine) as s:
            av = AgentVersion(
                project_id=body.project_id,
                commit=body.commit,
                framework=body.framework,
                label=body.label,
            )
            s.add(av)
            s.commit()
            s.refresh(av)
            return {
                "id": av.id,
                "project_id": av.project_id,
                "commit": av.commit,
                "framework": av.framework,
                "label": av.label,
                "created_at": av.created_at.isoformat(),
            }

    return app


app = create_app()
