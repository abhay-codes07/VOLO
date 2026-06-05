"""Golden snapshot tests — schema-level regression guards (bible §7.3).

These tests freeze the on-the-wire JSON shape of the canonical types:

* ``Recording`` v1.0.0 — every field, including null sentinels.
* ``ReliabilityReport`` — at the structural level (presence of every metric key).
* ``Diff`` — the kind union + presence of ``first_diverging_step``.

If any of these shapes change accidentally, a downstream consumer (the dashboard,
volo-langgraph, the OTel importer) will silently break. We catch that here before the
user sees it.
"""

from __future__ import annotations

import json
from pathlib import Path

from volo_core import (
    DecisionPayload,
    ModelCallPayload,
    Recording,
    ToolCallPayload,
)
from volo_diff import compute_diff
from volo_reliability import (
    METRIC_NAMES,
    aggregate_runs,
    compose_report,
)

GOLDEN_DIR = Path(__file__).parent / "golden"


# ── Recording schema ─────────────────────────────────────────────────────────


def test_recording_v1_canonical_round_trip() -> None:
    """A frozen Recording JSON loads and re-dumps with the same key set."""
    golden = json.loads((GOLDEN_DIR / "recording_v1_canonical.json").read_text(encoding="utf-8"))
    rec = Recording.model_validate(golden)
    rebuilt = rec.model_dump(mode="python", by_alias=True)
    assert _keyset(rebuilt) == _keyset(golden)


def test_recording_v1_field_inventory_is_stable() -> None:
    """The Recording's top-level field set is part of the public contract."""
    sample = Recording().model_dump(by_alias=True)
    assert set(sample.keys()) == {
        "recording_schema_version",
        "run_id",
        "created_at",
        "redaction_applied",
        "agent_meta",
        "steps",
        "final_output",
        "env_snapshot",
        "tool_specs",
    }


def test_step_payload_discriminator_unions_are_stable() -> None:
    for payload, expected_keys in [
        (
            ModelCallPayload(provider="p", model="m", request={}, response={}),
            {"type", "provider", "model", "request", "response"},
        ),
        (
            ToolCallPayload(tool="t", request={}, response={}),
            {"type", "tool", "request", "response"},
        ),
        (DecisionPayload(label="d"), {"type", "label", "options", "chosen", "rationale"}),
    ]:
        assert set(payload.model_dump().keys()) == expected_keys


# ── ReliabilityReport ────────────────────────────────────────────────────────


def test_reliability_report_aggregate_carries_all_four_metrics() -> None:
    r = Recording()
    sub = aggregate_runs([r], scenario_op="x", failure_class="y", seed=0)
    report = compose_report(r, [sub])
    blob = report.model_dump()
    assert set(blob["aggregate"].keys()) == set(METRIC_NAMES)
    assert blob["verdict"] in ("ship", "no_ship")


def test_reliability_report_field_inventory_is_stable() -> None:
    r = Recording()
    sub = aggregate_runs([r], scenario_op="x", failure_class="y", seed=0)
    report = compose_report(r, [sub])
    assert set(report.model_dump().keys()) == {
        "baseline_run_id",
        "agent_name",
        "fail_under",
        "aggregate",
        "verdict",
        "scenarios",
        "recorded_tokens",
        "recorded_cost_usd",
        "simulated_cost_usd",
    }


def test_scenario_report_field_inventory_is_stable() -> None:
    r = Recording()
    sub = aggregate_runs([r], scenario_op="x", failure_class="y", seed=0)
    assert set(sub.model_dump().keys()) == {
        "scenario_op",
        "failure_class",
        "seed",
        "n_runs",
        "metrics",
        "histogram",
        "applicable",
        "notes",
    }


# ── Diff shape ───────────────────────────────────────────────────────────────


def test_diff_top_level_fields_are_stable() -> None:
    a = Recording()
    b = Recording()
    diff = compute_diff(a, b)
    blob = diff.model_dump()
    assert set(blob.keys()) == {
        "baseline_run_id",
        "candidate_run_id",
        "first_diverging_step",
        "aligned_steps",
        "summary",
    }


def test_step_diff_kind_union_is_stable() -> None:
    # Construct a known diverging pair and inspect aligned step kinds.
    a = Recording()
    a.add_step(ToolCallPayload(tool="t", request={}, response={"x": 1}))
    b = Recording()
    b.add_step(ToolCallPayload(tool="t", request={}, response={"x": 2}))
    diff = compute_diff(a, b)
    kinds = {s.kind for s in diff.aligned_steps}
    assert kinds.issubset({"same", "added", "removed", "changed"})


# ── helpers ──────────────────────────────────────────────────────────────────


def _keyset(value: object) -> object:
    """Recursively collect the dict-key structure of ``value`` for compare."""
    if isinstance(value, dict):
        return {k: _keyset(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_keyset(v) for v in value]
    return type(value).__name__
