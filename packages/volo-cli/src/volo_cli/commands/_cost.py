"""Shared cost/token formatting for CLI commands (bible §11 — visible cost in CLI output)."""

from __future__ import annotations

from volo_reliability import ReliabilityReport


def cost_lines(report: ReliabilityReport) -> list[str]:
    """Render a compact cost/token summary, or a single neutral line if usage is unknown.

    Tells the core value-prop story: the recording cost real money once; replaying it in this
    run cost ~nothing.
    """
    if report.recorded_cost_usd is None and report.recorded_tokens is None:
        return ["cost: no token/cost usage recorded in this trace"]

    lines = ["cost:"]
    tokens = report.recorded_tokens
    tok = f"{tokens:,} tok" if tokens is not None else "— tok"
    rec = report.recorded_cost_usd or 0.0
    lines.append(f"  recorded (live run)   ${rec:.4f}   {tok}")
    lines.append(f"  simulated (this run)  ${report.simulated_cost_usd:.4f}   (replayed)")
    saved = report.saved_cost_usd
    if saved is not None:
        lines.append(f"  saved                 ${saved:.4f}")
    return lines


def cost_cap_breach(report: ReliabilityReport, max_usd: float | None) -> str | None:
    """Return a breach message if this run's real spend exceeded ``max_usd``, else ``None``.

    The cap guards *this run's* API spend (``simulated_cost_usd``) — $0 under Tier-1 replay, so
    it only ever fires once an opt-in frontier judge/synthesizer actually spends money (bible
    §11 "hard cap"). The recorded (historical) cost is informational and never capped.
    """
    if max_usd is None:
        return None
    if report.simulated_cost_usd > max_usd:
        return (
            f"cost cap exceeded: this run spent ${report.simulated_cost_usd:.4f} "
            f"> --max-cost-usd ${max_usd:.4f}"
        )
    return None
