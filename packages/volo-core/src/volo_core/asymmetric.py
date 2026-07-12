"""Ed25519 asymmetric signing primitive (post-v5.0; ADR-0028 / ADR-0037).

The v1 signing across packs (M25), evidence (M29), and certificates (M33) is HMAC-SHA256 — a
*symmetric* shared secret, fine for a private trust domain. Ed25519 adds *asymmetric* signing: the
issuer signs with a private key and anyone verifies with the public key, holding no secret that
could forge new signatures — what a public credential (a certificate, an evidence pack) needs.

This module is stdlib-free of the crypto itself: it lazily imports ``cryptography`` and raises a
clear error if it isn't installed, so the OSS core stays lean and only signing paths that opt into
asymmetric pull the dependency.
"""

from __future__ import annotations

from typing import Any

ED25519 = "ed25519"


class CryptographyUnavailable(RuntimeError):
    """Raised when an asymmetric operation is attempted without the ``cryptography`` package."""


def _load() -> tuple[Any, Any]:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via the guard test
        raise CryptographyUnavailable(
            "Ed25519 signing needs the 'cryptography' package "
            "(pip install cryptography, or install a volo package that depends on it)."
        ) from exc
    return serialization, ed25519


def generate_keypair() -> tuple[str, str]:
    """Return a fresh ``(private_pem, public_pem)`` Ed25519 keypair as PEM strings."""
    serialization, ed25519 = _load()
    priv = ed25519.Ed25519PrivateKey.generate()
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


def sign_ed25519(message: bytes, private_pem: str) -> str:
    """Sign ``message`` with an Ed25519 private-key PEM; return a hex signature."""
    serialization, _ = _load()
    key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
    return str(key.sign(message).hex())


def verify_ed25519(message: bytes, signature_hex: str, public_pem: str) -> bool:
    """True iff ``signature_hex`` is a valid Ed25519 signature of ``message`` under ``public_pem``."""
    serialization, _ = _load()
    try:
        from cryptography.exceptions import InvalidSignature

        key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        key.verify(bytes.fromhex(signature_hex), message)
        return True
    except (InvalidSignature, ValueError):
        return False
