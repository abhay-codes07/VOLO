"""Ingest — production traces in, redacted corpus entries out (M13).

Two doors into the bank:

* ``pull`` — sample production OTel traces (JSONL / OTLP JSON / bare array, via the M7
  ``import_otel_trace`` seam). **The redaction pass always runs before anything touches disk**
  (bible §7.5) — banked traces are fixtures people commit.
* ``adopt`` — turn one existing recording (typically a production *failure* trace) into a
  permanent corpus entry: every outage makes the suite stronger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from volo_core import Recording, RedactionConfig, redact_recording
from volo_sdk import import_otel_trace
from volo_shadow.corpus import CorpusBank, CorpusEntry

_TRACE_SUFFIXES = {".json", ".jsonl"}


@dataclass
class PullResult:
    imported: list[CorpusEntry] = field(default_factory=list)
    duplicates: int = 0
    empty: int = 0

    def summary(self) -> str:
        return f"{len(self.imported)} banked, {self.duplicates} duplicate(s), {self.empty} empty"


def pull(
    source: Path | str,
    bank: CorpusBank,
    *,
    agent_name: str | None = None,
    framework: str = "otel",
    redaction: RedactionConfig | None = None,
    tag: str = "shadow",
) -> PullResult:
    """Import every OTel trace under ``source`` (file or directory) into the bank."""
    src = Path(source)
    if src.is_dir():
        files = sorted(p for p in src.iterdir() if p.suffix.lower() in _TRACE_SUFFIXES)
    else:
        files = [src]

    result = PullResult()
    for f in files:
        recording = import_otel_trace(f, agent_name=agent_name, framework=framework)
        if not recording.steps:
            result.empty += 1
            continue
        recording = redact_recording(recording, redaction)
        entry = bank.add(recording, source=tag)
        if entry is None:
            result.duplicates += 1
        else:
            result.imported.append(entry)
    return result


def adopt(
    recording_path: Path | str,
    bank: CorpusBank,
    *,
    redaction: RedactionConfig | None = None,
    tag: str = "incident",
) -> CorpusEntry | None:
    """Bank one existing Recording file. Redacts first unless the file already was."""
    recording = Recording.from_json(Path(recording_path).read_text(encoding="utf-8"))
    if not recording.redaction_applied:
        recording = redact_recording(recording, redaction)
    return bank.add(recording, source=tag)
