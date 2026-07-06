"""Recording persistence v2 — gzip-aware save/load + a schema-migration seam (M19).

Two capabilities on top of ``Recording.to_json`` / ``from_json``:

* **Compression.** ``save_recording`` / ``load_recording`` transparently gzip when the path ends
  in ``.gz``. Banked corpora (M13) and long recordings compress ~5-15x; nothing else changes.
* **Migration.** ``load_recording`` upgrades an older ``recording_schema_version`` through the
  registered migration chain *before* validation, so a v1 recording keeps loading after a schema
  bump instead of hard-failing. ``Recording.from_json`` stays strict (current version only) for
  internal round-trips; ``load_recording`` is the tolerant front door. See ADR-0023.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from volo_core.recording import RECORDING_SCHEMA_VERSION, Recording

# version -> (next_version, migrate_fn). A migration takes a raw recording dict at ``version`` and
# returns it at ``next_version``. Chains apply in order until the current version is reached.
_MIGRATIONS: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {}


def register_migration(
    from_version: str,
    to_version: str,
    fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Register a one-step upgrade ``from_version`` → ``to_version`` (ADR-0023)."""
    _MIGRATIONS[from_version] = (to_version, fn)


def migrate_raw(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a raw recording dict to the current schema version via the migration chain."""
    version = str(data.get("recording_schema_version", RECORDING_SCHEMA_VERSION))
    seen: set[str] = set()
    while version != RECORDING_SCHEMA_VERSION:
        if version in seen:
            raise ValueError(f"migration cycle detected at schema version {version!r}")
        seen.add(version)
        step = _MIGRATIONS.get(version)
        if step is None:
            raise ValueError(
                f"no migration path from recording_schema_version {version!r} to "
                f"{RECORDING_SCHEMA_VERSION!r}; this build cannot read that recording.",
            )
        to_version, fn = step
        data = fn(data)
        data["recording_schema_version"] = to_version
        version = to_version
    return data


def _is_gzip(path: Path) -> bool:
    return path.suffix == ".gz"


def save_recording(recording: Recording, path: Path | str, *, indent: int = 2) -> Path:
    """Write ``recording`` as JSON, gzip-compressed when ``path`` ends in ``.gz``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    blob = recording.to_json(indent=indent) + "\n"
    if _is_gzip(target):
        target.write_bytes(gzip.compress(blob.encode("utf-8")))
    else:
        target.write_text(blob, encoding="utf-8")
    return target


def _read_text(path: Path) -> str:
    if _is_gzip(path):
        return gzip.decompress(path.read_bytes()).decode("utf-8")
    return path.read_text(encoding="utf-8")


def load_recording(path: Path | str) -> Recording:
    """Load a recording (plain or ``.gz``), migrating older schema versions first."""
    raw = json.loads(_read_text(Path(path)))
    if not isinstance(raw, dict):
        raise ValueError(f"recording file {path} is not a JSON object")
    return Recording.model_validate(migrate_raw(raw))


def recording_header(path: Path | str) -> dict[str, Any]:
    """Cheap inspection: read a recording's metadata + step count without validating every step.

    Useful for listing large corpora — parses the JSON but skips Pydantic validation of the
    (potentially thousands of) steps.
    """
    raw = json.loads(_read_text(Path(path)))
    steps = raw.get("steps") or []
    return {
        "run_id": raw.get("run_id"),
        "recording_schema_version": raw.get("recording_schema_version"),
        "agent_meta": raw.get("agent_meta") or {},
        "n_steps": len(steps) if isinstance(steps, list) else 0,
        "redaction_applied": bool(raw.get("redaction_applied")),
    }
