"""Versioned Recording schema. See ADR-0003 and bible §9.1."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RECORDING_SCHEMA_VERSION = "1.0.0"


def new_run_id() -> str:
    """Return a fresh `run_id` — UUID v4 prefixed by epoch ms for chronological sortability."""
    ts_ms = int(time.time() * 1000)
    return f"{ts_ms:013d}-{uuid.uuid4()}"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Mutable(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- step payloads ----------


class ModelCallPayload(_Mutable):
    type: Literal["model_call"] = "model_call"
    provider: str
    model: str
    request: dict[str, Any]
    response: dict[str, Any] | None = None


class ToolCallPayload(_Mutable):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    request: dict[str, Any]
    response: dict[str, Any] | None = None


class DecisionPayload(_Mutable):
    """An agent's internal branching point — e.g., "route to tool X" vs "terminate"."""

    type: Literal["decision"] = "decision"
    label: str
    options: list[str] = Field(default_factory=list)
    chosen: str | None = None
    rationale: str | None = None


StepPayload = Annotated[
    ModelCallPayload | ToolCallPayload | DecisionPayload,
    Field(discriminator="type"),
]


# ---------- step ----------


class Step(_Mutable):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    started_at: str = Field(default_factory=_utcnow_iso)
    latency_ms: float | None = None
    tokens: int | None = None
    cost_usd: float | None = None
    payload: StepPayload

    @property
    def type(self) -> str:
        return self.payload.type


# ---------- tool specs / env / meta ----------


class ToolSpec(_Frozen):
    """Declarative tool description. Optional in v1 but lifts simulator fidelity (bible §9.2)."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    source_hint: str | None = Field(
        default=None,
        description="Pointer to source file or OpenAPI doc — used by the Tier-2 simulator.",
    )


class EnvSnapshot(_Mutable):
    """Opaque initial-state blob the simulator can use to seed the world."""

    files: dict[str, str] = Field(default_factory=dict)
    kv: dict[str, Any] = Field(default_factory=dict)


class RunMeta(_Mutable):
    framework: str = "unknown"
    framework_version: str | None = None
    agent_name: str | None = None
    model_config_: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ---------- top-level Recording ----------


class Recording(_Mutable):
    """A single agent run, serialized.

    Stored as pretty-printed JSON at ``./.volo/recordings/<run_id>.json`` in local mode.
    """

    recording_schema_version: str = RECORDING_SCHEMA_VERSION
    run_id: str = Field(default_factory=new_run_id)
    created_at: str = Field(default_factory=_utcnow_iso)
    redaction_applied: bool = False
    agent_meta: RunMeta = Field(default_factory=RunMeta)
    steps: list[Step] = Field(default_factory=list)
    final_output: Any = None
    env_snapshot: EnvSnapshot | None = None
    tool_specs: list[ToolSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_schema_version(self) -> Recording:
        if self.recording_schema_version != RECORDING_SCHEMA_VERSION:
            # Future: dispatch to migrations/. v1 refuses unknown versions explicitly.
            raise ValueError(
                f"Unsupported recording_schema_version: {self.recording_schema_version!r}. "
                f"This build understands {RECORDING_SCHEMA_VERSION!r}.",
            )
        return self

    def add_step(self, payload: StepPayload, *, parent_id: str | None = None) -> Step:
        step = Step(parent_id=parent_id, payload=payload)
        self.steps.append(step)
        return step

    def total_tokens(self) -> int | None:
        """Sum of per-step ``tokens``, or ``None`` if no step carries usage data."""
        vals = [s.tokens for s in self.steps if s.tokens is not None]
        return sum(vals) if vals else None

    def total_cost_usd(self) -> float | None:
        """Sum of per-step ``cost_usd``, or ``None`` if no step carries cost data."""
        vals = [s.cost_usd for s in self.steps if s.cost_usd is not None]
        return sum(vals) if vals else None

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent, by_alias=True)

    @classmethod
    def from_json(cls, raw: str) -> Recording:
        return cls.model_validate_json(raw)
