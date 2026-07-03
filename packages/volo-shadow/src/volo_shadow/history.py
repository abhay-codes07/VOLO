"""Snapshot history — the reliability surface over time, one JSONL line per check (M14).

Every ``volo shadow check`` appends ``{at, snapshot, drift}`` to a plain JSONL file
(default ``./.volo/shadow-history.jsonl``). Committable, greppable, no database — and enough
to answer the two trend questions: *how is the fleet doing over time?* (``fleet_series``) and
*how is this one banked trace doing?* (``trace_series``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from volo_shadow.drift import DriftReport


class SnapshotHistory:
    """Append-only JSONL of nightly snapshots + their drift verdicts."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(
        self,
        snapshot: dict[str, Any],
        *,
        drift: DriftReport | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
            "snapshot": snapshot,
            "drift": drift.to_dict() if drift is not None else None,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n")
        return entry

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn write must not take the whole history down
            if isinstance(parsed, dict):
                out.append(parsed)
        return out

    def fleet_series(self) -> list[dict[str, Any]]:
        """One point per check: each dimension averaged across every banked trace."""
        series: list[dict[str, Any]] = []
        for entry in self.entries():
            traces = ((entry.get("snapshot") or {}).get("entries") or {}).values()
            sums: dict[str, list[float]] = {}
            for trace in traces:
                for dim, value in (trace.get("aggregate") or {}).items():
                    if isinstance(value, int | float):
                        sums.setdefault(str(dim), []).append(float(value))
            drift = entry.get("drift") or {}
            series.append(
                {
                    "at": entry.get("at"),
                    "aggregate": {dim: sum(vs) / len(vs) for dim, vs in sums.items()},
                    "drifted": bool(drift.get("drifted")),
                    "findings": len(drift.get("findings") or []),
                    "traces": len((entry.get("snapshot") or {}).get("entries") or {}),
                }
            )
        return series

    def trace_series(self, run_id: str) -> list[dict[str, Any]]:
        """One point per check for a single banked trace (absent nights are skipped)."""
        series: list[dict[str, Any]] = []
        for entry in self.entries():
            trace = ((entry.get("snapshot") or {}).get("entries") or {}).get(run_id)
            if trace is None:
                continue
            series.append(
                {
                    "at": entry.get("at"),
                    "aggregate": dict(trace.get("aggregate") or {}),
                    "verdict": trace.get("verdict"),
                }
            )
        return series
