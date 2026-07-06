"""Evidence packs: control evaluation, determinism, checksum + signature sealing."""

from __future__ import annotations

from typing import Any

from volo_compliance import (
    EvidencePack,
    build_evidence_pack,
    render_html,
    render_markdown,
    sign_evidence,
    verify_evidence,
)
from volo_redteam import SafetyAnnex
from volo_reliability import ReliabilityReport


def _reliability(verdict: str = "ship") -> ReliabilityReport:
    return ReliabilityReport(
        baseline_run_id="r1",
        aggregate={"trajectory_determinism": 1.0, "faithfulness": 1.0},
        verdict=verdict,  # type: ignore[arg-type]
        scenarios=[],
    )


def _safety(verdict: str = "safe", compromised: int = 0) -> SafetyAnnex:
    return SafetyAnnex(
        baseline_run_id="r1",
        verdict=verdict,
        attacks_run=54,  # type: ignore[arg-type]
        compromised=compromised,
        findings=[],
    )


def _drift(drifted: bool = False) -> dict[str, Any]:
    return {"drifted": drifted, "findings": [{"x": 1}] if drifted else []}


def test_full_evidence_satisfies_all_controls() -> None:
    pack = build_evidence_pack(
        agent_name="bot",
        frameworks=["eu_ai_act", "iso_42001", "soc2"],
        reliability=_reliability("ship"),
        safety=_safety("safe"),
        drift=_drift(False),
    )
    assert pack.all_satisfied
    assert pack.counts()["unmet"] == 0
    assert pack.checksum  # sealed


def test_missing_evidence_marks_controls_unmet() -> None:
    # only reliability → monitoring + security controls are unmet
    pack = build_evidence_pack(
        agent_name="bot", frameworks=["eu_ai_act"], reliability=_reliability("ship")
    )
    states = {c.control_id: c.state for c in pack.controls}
    assert states["Art.15-robustness"] == "satisfied"  # reliability present + passing
    assert states["Art.72-monitoring"] == "unmet"  # no drift evidence
    assert states["Art.15-cybersecurity"] == "unmet"  # no red-team evidence


def test_failing_evidence_is_partial_not_satisfied() -> None:
    pack = build_evidence_pack(
        agent_name="bot",
        frameworks=["eu_ai_act"],
        reliability=_reliability("no_ship"),
        safety=_safety("vulnerable", compromised=3),
        drift=_drift(True),
    )
    states = {c.control_id: c.state for c in pack.controls}
    assert states["Art.15-robustness"] == "partial"  # present but not passing
    assert states["Art.9-risk-mgmt"] == "partial"  # weakest of two present-but-failing
    assert states["Art.72-monitoring"] == "partial"  # drifted


def test_checksum_is_deterministic_excluding_timestamp() -> None:
    a = build_evidence_pack(
        agent_name="bot",
        frameworks=["soc2"],
        reliability=_reliability(),
        generated_at="2026-01-01T00:00:00Z",
    )
    b = build_evidence_pack(
        agent_name="bot",
        frameworks=["soc2"],
        reliability=_reliability(),
        generated_at="2026-12-31T23:59:59Z",
    )
    assert a.checksum == b.checksum  # timestamp is not part of the checksum


def test_sign_and_verify_roundtrip() -> None:
    pack = build_evidence_pack(agent_name="bot", frameworks=["soc2"], reliability=_reliability())
    signed = sign_evidence(pack, publisher="acme", secret="s3cret")
    assert verify_evidence(signed, {"acme": "s3cret"}) is True
    assert verify_evidence(signed, {"acme": "wrong"}) is False


def test_tampering_breaks_verification() -> None:
    pack = build_evidence_pack(agent_name="bot", frameworks=["soc2"], reliability=_reliability())
    signed = sign_evidence(pack, publisher="acme", secret="s3cret")
    tampered = signed.model_copy(update={"agent_name": "evil-bot"})
    assert verify_evidence(tampered, {"acme": "s3cret"}) is False


def test_renderers_and_json_roundtrip() -> None:
    pack = build_evidence_pack(
        agent_name="bot", frameworks=["eu_ai_act"], reliability=_reliability(), safety=_safety()
    )
    assert render_markdown(pack).startswith("# Compliance evidence — bot")
    assert render_html(pack).lstrip().startswith("<!doctype html>")
    restored = EvidencePack.model_validate_json(pack.to_json())
    assert restored.checksum == pack.checksum
