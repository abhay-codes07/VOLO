"""M34 v5.0 capstone — the whole platform composes end to end on one recording.

record → reliability → red-team → certify → evidence pack → (cloud ingest). This is the
integration proof that the pillars built across M1-M33 are one coherent product, not a pile of
packages: a single baseline recording flows through every gate and out the other side as a signed
certificate and a signed evidence pack, then lands in the commercial control plane.
"""

from __future__ import annotations

from typing import Any

import pytest
from examples.vulnerable_agent import guarded_summarizer, naive_summarizer

from volo_core import Recording, ToolCallPayload


def _baseline() -> Recording:
    """The single baseline recording everything in the pipeline flows from."""
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    return rec


def test_full_pipeline_certifies_and_packages_a_good_agent() -> None:
    from volo_certify import certify, sign_certificate, verify_certificate
    from volo_compliance import build_evidence_pack, sign_evidence, verify_evidence
    from volo_redteam import run_redteam
    from volo_reliability import METRIC_NAMES
    from volo_runner import orchestrate

    baseline = _baseline()

    # 1. reliability
    report = orchestrate(baseline, guarded_summarizer)
    assert set(report.aggregate) == set(METRIC_NAMES)
    assert report.verdict in {"ship", "no_ship"}

    # 2. red-team safety
    annex = run_redteam(baseline, guarded_summarizer, agent_name="guarded")
    assert annex.verdict == "safe" and annex.compromised == 0

    # 3. certification composes 1+2, signed + verifiable
    cert = sign_certificate(
        certify(baseline, guarded_summarizer, agent_name="guarded"),
        publisher="volo-official",
        secret="secret",
    )
    assert cert.passed is True
    assert verify_certificate(cert, {"volo-official": "secret"}) is True

    # 4. compliance evidence pack over the same reliability + safety results, signed + verifiable
    pack = sign_evidence(
        build_evidence_pack(
            agent_name="guarded", frameworks=["eu_ai_act"], reliability=report, safety=annex
        ),
        publisher="volo-official",
        secret="secret",
    )
    assert verify_evidence(pack, {"volo-official": "secret"}) is True
    assert pack.controls, "evidence pack should map at least one control"


def test_full_pipeline_rejects_a_vulnerable_agent() -> None:
    """The same pipeline must *deny* an unsafe agent — the gate has teeth."""
    from volo_certify import certify
    from volo_redteam import run_redteam

    baseline = _baseline()
    annex = run_redteam(baseline, naive_summarizer, agent_name="naive")
    assert annex.verdict == "vulnerable" and annex.compromised > 0

    cert = certify(baseline, naive_summarizer, agent_name="naive")
    assert cert.passed is False
    assert any("not safe" in r for r in cert.reasons)


def test_certificate_flows_into_cloud_history(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The capstone reaches the commercial plane: a certified run's report ingests into a workspace."""
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'v5.db').as_posix()}")
    from volo_cloud import service

    from volo_core.storage import get_engine, init_schema
    from volo_runner import orchestrate

    engine = get_engine()
    init_schema(engine)
    report = orchestrate(_baseline(), guarded_summarizer)

    team = service.create_team(engine, slug="acme", name="Acme")
    ws = service.create_workspace(engine, team_id=team.id, slug="prod", name="Prod")
    service.ingest_reliability_report(engine, workspace_id=ws.id, report=report)

    stored = service.list_reports(engine, workspace_id=ws.id)
    assert len(stored) == 1 and stored[0].verdict == report.verdict
