"""Step-level diff between two Recordings (ADR-0007)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, canonical_json

StepKind = Literal["same", "added", "removed", "changed"]


def _shape(rec: Recording) -> list[tuple[str, str]]:
    """The shape of a recording — same definition as volo_reliability."""
    out: list[tuple[str, str]] = []
    for step in rec.steps:
        p = step.payload
        if p.type == "model_call":
            out.append(("model_call", f"{p.provider}/{p.model}"))
        elif p.type == "tool_call":
            out.append(("tool_call", p.tool))
        else:
            out.append(("decision", p.label))
    return out


def _lcs(a: list[tuple[str, str]], b: list[tuple[str, str]]) -> list[tuple[int, int]]:
    """Return matched (i_in_a, j_in_b) index pairs from the LCS of a and b."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    pairs: list[tuple[int, int]] = []
    i, j = 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _step_summary(rec: Recording, idx: int) -> dict[str, Any]:
    s = rec.steps[idx]
    p = s.payload
    base: dict[str, Any] = {"step_id": s.step_id, "type": p.type}
    if p.type == "model_call":
        base.update(provider=p.provider, model=p.model, request=p.request, response=p.response)
    elif p.type == "tool_call":
        base.update(tool=p.tool, request=p.request, response=p.response)
    else:
        base.update(label=p.label, chosen=p.chosen)
    return base


def _changed_keys(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k in ("request", "response", "chosen"):
        if (k in a or k in b) and canonical_json(a.get(k)) != canonical_json(b.get(k)):
            out.append(k)
    return out


class StepDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: StepKind
    a_index: int | None = None
    b_index: int | None = None
    a: dict[str, Any] | None = None
    b: dict[str, Any] | None = None
    changed_keys: list[str] = Field(default_factory=list)


class Diff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    candidate_run_id: str
    first_diverging_step: int | None
    aligned_steps: list[StepDiff]
    summary: str

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def compute_diff(baseline: Recording, candidate: Recording) -> Diff:
    """Compute the step-level Diff."""
    a_shape = _shape(baseline)
    b_shape = _shape(candidate)
    matches = _lcs(a_shape, b_shape)

    aligned: list[StepDiff] = []
    i = j = 0
    for ai, bj in matches:
        while i < ai:
            aligned.append(StepDiff(kind="removed", a_index=i, a=_step_summary(baseline, i)))
            i += 1
        while j < bj:
            aligned.append(StepDiff(kind="added", b_index=j, b=_step_summary(candidate, j)))
            j += 1
        a_sum = _step_summary(baseline, ai)
        b_sum = _step_summary(candidate, bj)
        changed = _changed_keys(a_sum, b_sum)
        aligned.append(
            StepDiff(
                kind="changed" if changed else "same",
                a_index=ai,
                b_index=bj,
                a=a_sum,
                b=b_sum,
                changed_keys=changed,
            ),
        )
        i = ai + 1
        j = bj + 1
    while i < len(baseline.steps):
        aligned.append(StepDiff(kind="removed", a_index=i, a=_step_summary(baseline, i)))
        i += 1
    while j < len(candidate.steps):
        aligned.append(StepDiff(kind="added", b_index=j, b=_step_summary(candidate, j)))
        j += 1

    first_div: int | None = next(
        (idx for idx, sd in enumerate(aligned) if sd.kind != "same"),
        None,
    )

    if first_div is None:
        summary = "no trajectory divergence"
    else:
        sd = aligned[first_div]
        summary = f"first divergence at aligned step #{first_div}: {sd.kind}"
        if sd.kind == "changed":
            summary += f" (keys: {', '.join(sd.changed_keys)})"

    return Diff(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        first_diverging_step=first_div,
        aligned_steps=aligned,
        summary=summary,
    )


def format_diff(d: Diff) -> str:
    """Render a Diff as a terminal-friendly multi-line string."""
    lines = [
        f"diff  {d.baseline_run_id} -> {d.candidate_run_id}",
        f"      {d.summary}",
        "",
    ]
    for idx, sd in enumerate(d.aligned_steps):
        marker = {"same": "=", "added": "+", "removed": "-", "changed": "~"}[sd.kind]
        if sd.kind == "added":
            assert sd.b is not None
            lines.append(f"  [{idx:03d}] {marker} (cand[{sd.b_index}]) {sd.b['type']}")
        elif sd.kind == "removed":
            assert sd.a is not None
            lines.append(f"  [{idx:03d}] {marker} (base[{sd.a_index}]) {sd.a['type']}")
        else:
            assert sd.a is not None and sd.b is not None
            tail = f" keys={','.join(sd.changed_keys)}" if sd.changed_keys else ""
            lines.append(
                f"  [{idx:03d}] {marker} (base[{sd.a_index}]/cand[{sd.b_index}]) "
                f"{sd.a['type']}{tail}",
            )
    return "\n".join(lines)
