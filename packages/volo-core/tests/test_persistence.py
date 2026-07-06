"""Recording persistence v2: gzip round-trip, migration seam, cheap header (M19)."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from volo_core import (
    RECORDING_SCHEMA_VERSION,
    Recording,
    ToolCallPayload,
    load_recording,
    migrate_raw,
    recording_header,
    register_migration,
    save_recording,
)


def _rec() -> Recording:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="t", request={"q": "x"}, response={"hits": 3}))
    rec.final_output = {"answer": "ok"}
    return rec


def test_plain_json_roundtrip(tmp_path: Path) -> None:
    path = save_recording(_rec(), tmp_path / "r.json")
    assert path.suffix == ".json"
    loaded = load_recording(path)
    assert loaded.final_output == {"answer": "ok"}


def test_gzip_roundtrip_is_smaller_and_loads(tmp_path: Path) -> None:
    # a repetitive recording compresses well
    rec = Recording()
    for i in range(200):
        rec.add_step(ToolCallPayload(tool="search", request={"i": i}, response={"hits": i}))
    plain = save_recording(rec, tmp_path / "r.json")
    gz = save_recording(rec, tmp_path / "r.json.gz")

    assert gz.read_bytes()[:2] == b"\x1f\x8b"  # gzip magic
    assert gz.stat().st_size < plain.stat().st_size
    loaded = load_recording(gz)
    assert len(loaded.steps) == 200


def test_load_recording_reads_uncompressed_and_compressed(tmp_path: Path) -> None:
    p = tmp_path / "a.json"
    p.write_text(_rec().to_json(), encoding="utf-8")
    assert load_recording(p).final_output == {"answer": "ok"}

    g = tmp_path / "a.json.gz"
    g.write_bytes(gzip.compress(_rec().to_json().encode("utf-8")))
    assert load_recording(g).final_output == {"answer": "ok"}


def test_recording_header_is_cheap_and_correct(tmp_path: Path) -> None:
    path = save_recording(_rec(), tmp_path / "r.json.gz")
    header = recording_header(path)
    assert header["n_steps"] == 1
    assert header["recording_schema_version"] == RECORDING_SCHEMA_VERSION
    assert header["redaction_applied"] is False


def test_migration_upgrades_old_version() -> None:
    # register a fake "0.9.0 -> current" migration and prove load applies it
    def up(data: dict) -> dict:
        data.setdefault("tool_specs", [])
        return data

    register_migration("0.9.0", RECORDING_SCHEMA_VERSION, up)
    old = _rec().model_dump(mode="json", by_alias=True)
    old["recording_schema_version"] = "0.9.0"
    migrated = migrate_raw(old)
    assert migrated["recording_schema_version"] == RECORDING_SCHEMA_VERSION
    # and a full validate succeeds through the migration
    assert Recording.model_validate(migrated).final_output == {"answer": "ok"}


def test_unknown_version_without_migration_raises() -> None:
    old = _rec().model_dump(mode="json", by_alias=True)
    old["recording_schema_version"] = "0.0.1-unregistered"
    with pytest.raises(ValueError, match="no migration path"):
        migrate_raw(old)
