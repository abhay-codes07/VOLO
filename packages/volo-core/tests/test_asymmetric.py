"""Ed25519 primitive: keygen, sign, verify, tamper + wrong-key rejection."""

from __future__ import annotations

from volo_core import generate_keypair, sign_ed25519, verify_ed25519


def test_keypair_is_pem() -> None:
    priv, pub = generate_keypair()
    assert "PRIVATE KEY" in priv and "PUBLIC KEY" in pub


def test_sign_and_verify_roundtrip() -> None:
    priv, pub = generate_keypair()
    sig = sign_ed25519(b"volo-certified", priv)
    assert verify_ed25519(b"volo-certified", sig, pub) is True


def test_tampered_message_fails() -> None:
    priv, pub = generate_keypair()
    sig = sign_ed25519(b"original", priv)
    assert verify_ed25519(b"tampered", sig, pub) is False


def test_wrong_public_key_fails() -> None:
    priv, _ = generate_keypair()
    _, other_pub = generate_keypair()
    sig = sign_ed25519(b"msg", priv)
    assert verify_ed25519(b"msg", sig, other_pub) is False


def test_garbage_signature_is_rejected_not_raised() -> None:
    _, pub = generate_keypair()
    assert verify_ed25519(b"msg", "not-hex-zzzz", pub) is False
    assert verify_ed25519(b"msg", "abcd", pub) is False
