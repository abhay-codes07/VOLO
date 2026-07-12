"""Certificates can be signed asymmetrically (Ed25519) and verified with only the public key."""

from __future__ import annotations

from typing import Any

from volo_certify import certify, sign_certificate_ed25519, verify_certificate
from volo_core import Recording, ToolCallPayload, generate_keypair, get_active_environment


def _baseline() -> Recording:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    return rec


def _guarded(payload: Any = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    return {"answer": f"found {env.tool_registry().call('search', {'q': 'volo'})['hits']} results"}


def test_ed25519_signed_certificate_verifies_with_public_key() -> None:
    priv, pub = generate_keypair()
    cert = sign_certificate_ed25519(
        certify(_baseline(), _guarded, agent_name="guarded"),
        publisher="volo-official",
        private_pem=priv,
    )
    assert cert.signature is not None and cert.signature.algorithm == "ed25519"
    # a verifier holds only the PUBLIC key
    assert verify_certificate(cert, {"volo-official": pub}) is True


def test_ed25519_rejects_wrong_key_and_tamper() -> None:
    priv, _ = generate_keypair()
    _, other_pub = generate_keypair()
    cert = sign_certificate_ed25519(
        certify(_baseline(), _guarded, agent_name="g"), publisher="p", private_pem=priv
    )
    assert verify_certificate(cert, {"p": other_pub}) is False  # wrong key
    tampered = cert.model_copy(update={"volo_score": 100})
    assert verify_certificate(tampered, {"p": "x"}) is False  # checksum mismatch
