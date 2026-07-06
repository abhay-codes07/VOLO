"""Build an evidence pack from Volo artifacts and render it (M29)."""

from __future__ import annotations

from typing import Any

from volo_compliance.controls import controls_for
from volo_compliance.pack import (
    ControlStatus,
    EvidenceItem,
    EvidencePack,
    worst,
)
from volo_redteam import SafetyAnnex
from volo_reliability import ReliabilityReport


def _evidence_items(
    reliability: ReliabilityReport | None,
    safety: SafetyAnnex | None,
    drift: dict[str, Any] | None,
) -> dict[str, EvidenceItem]:
    items: dict[str, EvidenceItem] = {}
    if reliability is not None:
        items["reliability"] = EvidenceItem(
            kind="reliability",
            passed=reliability.verdict == "ship",
            summary=f"reliability verdict={reliability.verdict}, "
            f"{len(reliability.scenarios)} scenario(s)",
            detail={"verdict": reliability.verdict, "aggregate": dict(reliability.aggregate)},
        )
    if safety is not None:
        items["redteam_safety"] = EvidenceItem(
            kind="redteam_safety",
            passed=safety.verdict == "safe",
            summary=f"red-team verdict={safety.verdict}, "
            f"{safety.compromised}/{safety.attacks_run} attacks landed",
            detail={
                "verdict": safety.verdict,
                "compromised": safety.compromised,
                "attacks_run": safety.attacks_run,
            },
        )
    if drift is not None:
        drifted = bool(drift.get("drifted"))
        items["drift_monitoring"] = EvidenceItem(
            kind="drift_monitoring",
            passed=not drifted,
            summary=f"drift monitoring: {'DRIFT' if drifted else 'stable'}, "
            f"{len(drift.get('findings') or [])} finding(s)",
            detail={"drifted": drifted, "findings": len(drift.get("findings") or [])},
        )
    return items


def build_evidence_pack(
    *,
    agent_name: str,
    frameworks: list[str],
    reliability: ReliabilityReport | None = None,
    safety: SafetyAnnex | None = None,
    drift: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> EvidencePack:
    """Assemble evidence, evaluate every catalogued control, and seal the pack."""
    items = _evidence_items(reliability, safety, drift)

    controls: list[ControlStatus] = []
    for control in controls_for(frameworks):
        states = []
        missing = []
        for kind in control.requires:
            item = items.get(kind)
            if item is None:
                states.append("unmet")
                missing.append(kind)
            else:
                states.append("satisfied" if item.passed else "partial")
        state = worst(states)  # type: ignore[arg-type]
        if missing:
            note = f"missing evidence: {', '.join(missing)}"
        elif state == "partial":
            note = "evidence present but not passing"
        else:
            note = "satisfied by passing evidence"
        controls.append(
            ControlStatus(
                framework=control.framework,
                control_id=control.control_id,
                title=control.title,
                state=state,
                evidence_kinds=list(control.requires),
                note=note,
            )
        )

    pack = EvidencePack(
        agent_name=agent_name,
        frameworks=sorted(frameworks),
        generated_at=generated_at,
        evidence=list(items.values()),
        controls=controls,
    )
    return pack.sealed()


def render_markdown(pack: EvidencePack) -> str:
    c = pack.counts()
    lines = [
        f"# Compliance evidence — {pack.agent_name}",
        "",
        f"Frameworks: {', '.join(pack.frameworks)}  ·  "
        f"generated: {pack.generated_at or '(unset)'}  ·  checksum: `{pack.checksum[:16]}…`",
        "",
        f"**{c['satisfied']} satisfied · {c['partial']} partial · {c['unmet']} unmet**",
        "",
        "> Mapping aid, not legal advice. Evidence is deterministic, checksummed, and replayable.",
        "",
        "## Evidence",
        "",
    ]
    for e in pack.evidence:
        mark = "PASS" if e.passed else "FAIL"
        lines.append(f"- **{e.kind}** [{mark}] — {e.summary}")
    lines += [
        "",
        "## Controls",
        "",
        "| Framework | Control | Title | Status | Evidence |",
        "|---|---|---|---|---|",
    ]
    for ctl in pack.controls:
        lines.append(
            f"| {ctl.framework} | {ctl.control_id} | {ctl.title} | "
            f"{ctl.state} | {', '.join(ctl.evidence_kinds)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(pack: EvidencePack) -> str:
    color = {"satisfied": "#12b886", "partial": "#f59f00", "unmet": "#fa5252"}
    rows = "\n".join(
        f"<tr><td>{c.framework}</td><td>{c.control_id}</td><td>{c.title}</td>"
        f'<td style="color:{color[c.state]}">{c.state}</td>'
        f"<td>{', '.join(c.evidence_kinds)}</td></tr>"
        for c in pack.controls
    )
    counts = pack.counts()
    return _HTML.format(
        agent=pack.agent_name,
        frameworks=", ".join(pack.frameworks),
        checksum=pack.checksum[:16],
        satisfied=counts["satisfied"],
        partial=counts["partial"],
        unmet=counts["unmet"],
        rows=rows,
    )


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compliance evidence — {agent}</title>
<style>
  body{{background:#0A0E14;color:#c9d1d9;font:15px/1.5 ui-monospace,Menlo,monospace;
    max-width:900px;margin:3rem auto;padding:0 1rem}}
  h1{{color:#e6edf3;font-weight:600;letter-spacing:-.02em}}
  .sub{{color:#768390;margin-bottom:1.5rem}}
  table{{width:100%;border-collapse:collapse;margin-top:1rem}}
  th,td{{padding:.5rem .6rem;border-bottom:1px solid #21262d;text-align:left}}
  th{{color:#768390;font-weight:400;text-transform:uppercase;font-size:11px;letter-spacing:.08em}}
</style></head><body>
<h1>Compliance evidence — {agent}</h1>
<p class="sub">Frameworks: {frameworks} · checksum {checksum}… ·
<b style="color:#12b886">{satisfied} satisfied</b> ·
<b style="color:#f59f00">{partial} partial</b> ·
<b style="color:#fa5252">{unmet} unmet</b><br>
Mapping aid, not legal advice — evidence is deterministic, checksummed, and replayable.</p>
<table><thead><tr><th>Framework</th><th>Control</th><th>Title</th><th>Status</th><th>Evidence</th></tr></thead>
<tbody>
{rows}
</tbody></table>
</body></html>
"""
