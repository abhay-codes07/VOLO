"""Evidence packs support Ed25519 signatures verified with only the public key."""

from __future__ import annotations

from volo_compliance import build_evidence_pack, sign_evidence_ed25519, verify_evidence
from volo_core import generate_keypair


def _pack():  # type: ignore[no-untyped-def]
    return build_evidence_pack(agent_name="acme-bot", frameworks=["eu_ai_act"])


def test_ed25519_signed_evidence_verifies_with_public_key() -> None:
    priv, pub = generate_keypair()
    pack = sign_evidence_ed25519(_pack(), publisher="auditor", private_pem=priv)
    assert pack.signature is not None and pack.signature.algorithm == "ed25519"
    assert verify_evidence(pack, {"auditor": pub}) is True


def test_ed25519_evidence_rejects_wrong_key_and_tamper() -> None:
    priv, _ = generate_keypair()
    _, other = generate_keypair()
    pack = sign_evidence_ed25519(_pack(), publisher="auditor", private_pem=priv)
    assert verify_evidence(pack, {"auditor": other}) is False
    tampered = pack.model_copy(update={"agent_name": "evil-bot"})
    assert verify_evidence(tampered, {"auditor": "x"}) is False
