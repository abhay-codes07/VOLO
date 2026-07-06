"""Recorder — the developer-facing capture API.

The actual span-capture path (intercepting model + tool calls live) lands in a follow-up commit.
This module currently provides:

* the ``Recorder`` class with a stable surface (``record_step``, ``set_final_output``, ``save``)
* the ``record`` context manager
* a ``RecorderConfig`` dataclass

so that everything downstream (CLI, integrations, examples) can already be written against the
real API. See ``docs/STATUS.md`` "▶ RESUME HERE" for the exact next step.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from volo_core import (
    Recording,
    RedactionConfig,
    RunMeta,
    Step,
    current_recorder,
    redact_recording,
    save_recording,
)
from volo_core.recording import StepPayload


@dataclass
class RecorderConfig:
    """How a Recorder behaves at runtime.

    Args:
        data_dir: Where to write recordings. Defaults to ``./.volo``.
        apply_redaction: If True (default), the redaction pass runs before ``save()`` persists
            anything to disk.
        redaction: Tweaks for the redaction pass. ``None`` → default rules (bible §7.5).
        pretty: JSON indent on disk (set to 0 to minify).
        compress: If True, gzip the recording (``.json.gz``). Off by default (M19 / ADR-0023).
    """

    data_dir: Path = field(default_factory=lambda: Path(".volo"))
    apply_redaction: bool = True
    redaction: RedactionConfig | None = None
    pretty: int = 2
    compress: bool = False


class Recorder:
    """Build up a Recording, then write it to disk.

    Typical use is via the ``record()`` context manager. Direct use is also supported:

    .. code-block:: python

        rec = Recorder(agent_name="demo", framework="raw")
        rec.record_step(ModelCallPayload(provider="ollama", model="llama3.2:3b", request={...}))
        rec.set_final_output({"answer": "ok"})
        path = rec.save()
    """

    def __init__(
        self,
        *,
        agent_name: str | None = None,
        framework: str = "raw",
        framework_version: str | None = None,
        seed: int | None = None,
        config: RecorderConfig | None = None,
    ) -> None:
        self.config = config or RecorderConfig()
        self.recording = Recording(
            agent_meta=RunMeta(
                framework=framework,
                framework_version=framework_version,
                agent_name=agent_name,
                seed=seed,
            ),
        )

    # ---- manual capture API ----

    def record_step(self, payload: StepPayload, *, parent_id: str | None = None) -> Step:
        """Append a single trajectory step. Returns the created ``Step``."""
        return self.recording.add_step(payload, parent_id=parent_id)

    def set_final_output(self, value: Any) -> None:
        self.recording.final_output = value

    # ---- persistence ----

    def save(self, path: Path | str | None = None) -> Path:
        """Write the (optionally redacted) Recording to JSON and return the file path."""
        rec = (
            redact_recording(self.recording, self.config.redaction)
            if self.config.apply_redaction
            else self.recording
        )

        suffix = ".json.gz" if self.config.compress else ".json"
        if path is None:
            target_dir = self.config.data_dir / "recordings"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{rec.run_id}{suffix}"
        else:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)

        # save_recording gzips when the path ends in .gz; otherwise writes canonical UTF-8 JSON.
        return save_recording(rec, target, indent=self.config.pretty)


@contextmanager
def record(
    *,
    agent_name: str | None = None,
    framework: str = "raw",
    framework_version: str | None = None,
    seed: int | None = None,
    config: RecorderConfig | None = None,
    save_on_exit: bool = True,
    out: Path | str | None = None,
) -> Iterator[Recorder]:
    """Open a Recorder for the lifetime of a ``with`` block.

    Example::

        with record(agent_name="echo", framework="raw") as rec:
            rec.record_step(...)
            rec.set_final_output(...)
        # → recording saved to ./.volo/recordings/<run_id>.json
    """
    rec = Recorder(
        agent_name=agent_name,
        framework=framework,
        framework_version=framework_version,
        seed=seed,
        config=config,
    )
    with current_recorder(rec):
        try:
            yield rec
        finally:
            if save_on_exit:
                rec.save(out)
