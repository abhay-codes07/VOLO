"""Corpus bank — the ever-growing regression corpus of banked production traces (M13).

The bank is a directory (default ``./.volo/corpus``) of ordinary Recording JSON files plus an
``index.json``. Entries are deduplicated by a **content digest** over the trajectory (payloads +
final output, ignoring run ids and timestamps), so re-pulling the same production window is
idempotent — every incident banked once, forever.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from volo_core import Recording

INDEX_NAME = "index.json"


@dataclass(frozen=True)
class CorpusEntry:
    run_id: str
    digest: str
    source: str  # e.g. "shadow" (sampled traffic) | "incident" (adopted failure)
    agent_name: str | None
    framework: str
    steps: int
    file: str  # file name inside the bank directory
    added_at: str


class CorpusBank:
    """Filesystem-backed, index-tracked, digest-deduplicated recording corpus."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def add(self, recording: Recording, *, source: str = "shadow") -> CorpusEntry | None:
        """Bank a recording. Returns the new entry, or ``None`` if its content is already banked."""
        digest = content_digest(recording)
        entries = self.entries()
        if any(e.digest == digest for e in entries):
            return None
        self.root.mkdir(parents=True, exist_ok=True)
        file_name = f"{recording.run_id}.json"
        (self.root / file_name).write_text(recording.to_json() + "\n", encoding="utf-8")
        entry = CorpusEntry(
            run_id=recording.run_id,
            digest=digest,
            source=source,
            agent_name=recording.agent_meta.agent_name,
            framework=recording.agent_meta.framework,
            steps=len(recording.steps),
            file=file_name,
            added_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        entries.append(entry)
        self._write_index(entries)
        return entry

    def entries(self) -> list[CorpusEntry]:
        index = self.root / INDEX_NAME
        if not index.exists():
            return []
        raw = json.loads(index.read_text(encoding="utf-8"))
        return [CorpusEntry(**e) for e in raw.get("entries", [])]

    def load(self, entry: CorpusEntry) -> Recording:
        return Recording.from_json((self.root / entry.file).read_text(encoding="utf-8"))

    def load_all(self) -> list[tuple[CorpusEntry, Recording]]:
        return [(e, self.load(e)) for e in self.entries()]

    def _write_index(self, entries: list[CorpusEntry]) -> None:
        blob = {"entries": [asdict(e) for e in entries]}
        (self.root / INDEX_NAME).write_text(
            json.dumps(blob, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def content_digest(recording: Recording) -> str:
    """Digest of the trajectory *content* — stable across run ids, step ids, and timestamps."""
    material = {
        "steps": [s.payload.model_dump(mode="json", by_alias=True) for s in recording.steps],
        "final_output": recording.final_output,
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
