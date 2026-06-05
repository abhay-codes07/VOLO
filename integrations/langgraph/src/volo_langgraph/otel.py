"""LangGraph-flavored OTel import — thin alias over ``volo_sdk.import_otel_trace``."""

from __future__ import annotations

from pathlib import Path

from volo_core import Recording
from volo_sdk import import_otel_trace


def import_langgraph_otel(
    path: str | Path,
    *,
    agent_name: str | None = None,
) -> Recording:
    """Import a LangGraph OTel JSONL trace into a Volo Recording."""
    return import_otel_trace(path, agent_name=agent_name, framework="langgraph")
