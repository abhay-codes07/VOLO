"""Control catalog — maps compliance controls to the Volo evidence that satisfies them (M29).

A reasonable-effort mapping from three common frameworks to the kinds of evidence Volo produces.
This is a **mapping aid, not legal advice** — the value is that the evidence is deterministic,
signed, and replayable; how it maps to your obligations is your (and your auditor's) call.

Evidence kinds: ``reliability`` (a ReliabilityReport), ``redteam_safety`` (a SafetyAnnex),
``drift_monitoring`` (a shadow drift report).
"""

from __future__ import annotations

from dataclasses import dataclass

EvidenceKind = str  # "reliability" | "redteam_safety" | "drift_monitoring"
FRAMEWORKS: tuple[str, ...] = ("eu_ai_act", "iso_42001", "soc2")


@dataclass(frozen=True)
class Control:
    framework: str
    control_id: str
    title: str
    description: str
    requires: tuple[EvidenceKind, ...]


CONTROLS: tuple[Control, ...] = (
    # ── EU AI Act (deployer-relevant articles) ───────────────────────────────
    Control(
        "eu_ai_act",
        "Art.15-robustness",
        "Accuracy & robustness",
        "Demonstrated accuracy and robustness of the AI system (Art. 15).",
        ("reliability",),
    ),
    Control(
        "eu_ai_act",
        "Art.15-cybersecurity",
        "Resilience to adversarial manipulation",
        "Resilience against attempts to alter use or behaviour via adversarial inputs "
        "(Art. 15 cybersecurity).",
        ("redteam_safety",),
    ),
    Control(
        "eu_ai_act",
        "Art.9-risk-mgmt",
        "Risk management via testing",
        "Testing to identify and evaluate risks prior to and during use (Art. 9).",
        ("reliability", "redteam_safety"),
    ),
    Control(
        "eu_ai_act",
        "Art.72-monitoring",
        "Post-market monitoring",
        "Ongoing monitoring of the system's performance in operation (Art. 72).",
        ("drift_monitoring",),
    ),
    # ── ISO/IEC 42001 (AI management system) ─────────────────────────────────
    Control(
        "iso_42001",
        "8.3-verification",
        "AI system verification & validation",
        "Verification and validation of the AI system against requirements (Cl. 8.3).",
        ("reliability",),
    ),
    Control(
        "iso_42001",
        "8.4-security",
        "AI system security testing",
        "Security testing including adversarial evaluation (Cl. 8.4).",
        ("redteam_safety",),
    ),
    Control(
        "iso_42001",
        "9.1-monitoring",
        "Monitoring, measurement & analysis",
        "Monitoring and measurement of AI performance over time (Cl. 9.1).",
        ("drift_monitoring",),
    ),
    # ── SOC 2 (Common Criteria, adapted) ─────────────────────────────────────
    Control(
        "soc2",
        "CC7.1-testing",
        "Pre-deployment quality testing",
        "Testing to detect and correct deviations before deployment (CC7.1).",
        ("reliability",),
    ),
    Control(
        "soc2",
        "CC7.2-monitoring",
        "Ongoing anomaly monitoring",
        "Monitoring for anomalies indicative of degraded operation (CC7.2).",
        ("drift_monitoring",),
    ),
    Control(
        "soc2",
        "CC8.1-change",
        "Change-management verification",
        "Verification that changes do not regress reliability (CC8.1).",
        ("reliability",),
    ),
)


def controls_for(frameworks: list[str] | tuple[str, ...]) -> list[Control]:
    wanted = set(frameworks)
    return [c for c in CONTROLS if c.framework in wanted]
