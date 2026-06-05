"""Shared `--judge` resolution for CLI commands (bible §11, ADR-0011).

Maps a CLI judge name to a ``JudgeProvider`` (or ``None`` for the zero-cost heuristic).
The ``ollama`` and ``groq`` judges only make live calls at score time; if their backend is
unreachable they fall back to the heuristic, so selecting one never hard-fails a run.
"""

from __future__ import annotations

from typing import Any

JUDGE_CHOICES = ("heuristic", "ollama", "groq")


def resolve_judge(name: str) -> Any | None:
    """Return a ``JudgeProvider`` for ``name``, or ``None`` for the default heuristic.

    ``groq`` uses the free OpenAI-compatible judge (ADR-0011); it requires
    ``VOLO_OPENAI_COMPAT_OPT_IN=true`` + a ``GROQ_API_KEY`` at score time.
    """
    key = name.lower()
    if key == "heuristic":
        return None
    if key == "ollama":
        from volo_reliability import OllamaJudge

        return OllamaJudge()
    if key == "groq":
        from volo_reliability import OpenAICompatJudge

        return OpenAICompatJudge()
    import typer

    raise typer.BadParameter(f"--judge must be one of {JUDGE_CHOICES}, got {name!r}")
