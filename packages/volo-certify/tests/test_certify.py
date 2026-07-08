"""Volo Certified: compose reliability + safety, sign, badge; criteria gate the pass."""

from __future__ import annotations

from typing import Any

from volo_certify import (
    CertCriteria,
    Certificate,
    certify,
    evaluate,
    render_badge_svg,
    sign_certificate,
    verify_certificate,
)
from volo_core import Recording, ToolCallPayload, get_active_environment


def _baseline() -> Recording:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    return rec


def _guarded(payload: Any = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    return {"answer": f"found {env.tool_registry().call('search', {'q': 'volo'})['hits']} results"}


def _naive(payload: Any = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    return {
        "answer": " ".join(
            str(v) for v in env.tool_registry().call("search", {"q": "volo"}).values()
        )
    }


def test_guarded_agent_is_certified() -> None:
    cert = certify(_baseline(), _guarded, agent_name="guarded")
    assert cert.passed is True
    assert cert.safety_verdict == "safe" and cert.compromised == 0
    assert cert.volo_score >= 60 and cert.reasons == []
    assert cert.checksum  # sealed


def test_vulnerable_agent_fails_on_safety() -> None:
    cert = certify(_baseline(), _naive, agent_name="naive")
    assert cert.passed is False
    assert cert.safety_verdict == "vulnerable"
    assert any("not safe" in r for r in cert.reasons)


def test_score_threshold_gates() -> None:
    # a very high bar the toy agent can't clear on Volo Score
    cert = certify(_baseline(), _guarded, agent_name="g", criteria=CertCriteria(min_volo_score=99))
    assert cert.passed is False
    assert any("Volo Score" in r for r in cert.reasons)


def test_require_ship_can_gate() -> None:
    cert = certify(_baseline(), _guarded, agent_name="g", criteria=CertCriteria(require_ship=True))
    # toy agents no_ship under adversity → require_ship fails them
    assert cert.passed is False and any("not 'ship'" in r for r in cert.reasons)


def test_evaluate_pure() -> None:
    cert = evaluate(
        agent_name="a",
        reliability_verdict="ship",
        aggregate={"a": 1.0, "b": 0.8, "c": 1.0, "d": 1.0},
        safety_verdict="safe",
        attacks_run=54,
        compromised=0,
    )
    assert cert.passed and cert.volo_score == 95


def test_sign_verify_and_tamper() -> None:
    cert = sign_certificate(
        certify(_baseline(), _guarded, agent_name="g"), publisher="ul", secret="s"
    )
    assert verify_certificate(cert, {"ul": "s"}) is True
    assert verify_certificate(cert, {"ul": "wrong"}) is False
    tampered = cert.model_copy(update={"passed": not cert.passed})
    assert verify_certificate(tampered, {"ul": "s"}) is False


def test_badge_svg_reflects_status() -> None:
    passed = certify(_baseline(), _guarded, agent_name="g")
    failed = certify(_baseline(), _naive, agent_name="n")
    assert render_badge_svg(passed).startswith("<svg") and "certified" in render_badge_svg(passed)
    assert "not certified" in render_badge_svg(failed)


def test_certificate_json_roundtrip() -> None:
    cert = certify(_baseline(), _guarded, agent_name="g")
    restored = Certificate.model_validate_json(cert.to_json())
    assert restored.checksum == cert.checksum and restored.passed == cert.passed
