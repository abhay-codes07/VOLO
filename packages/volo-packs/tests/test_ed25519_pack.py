"""Packs support Ed25519 publisher signatures alongside HMAC; keyring mixes both."""

from __future__ import annotations

from volo_packs import (
    build_pack,
    sign_pack,
    sign_pack_ed25519,
    starter_items,
    verify_pack_signature,
)
from volo_packs.pack import Pack


def _pack(name: str = "demo") -> Pack:
    return build_pack(name=name, version="1.0.0", kind="attacks", items=starter_items("attacks"))


def test_ed25519_signed_pack_verifies_with_public_key() -> None:
    from volo_core import generate_keypair

    priv, pub = generate_keypair()
    pack = sign_pack_ed25519(_pack(), publisher="acme", private_pem=priv)
    assert pack.manifest.signature is not None and pack.manifest.signature.algorithm == "ed25519"
    assert verify_pack_signature(pack, {"acme": pub}) is True
    # wrong public key fails
    _, other = generate_keypair()
    assert verify_pack_signature(pack, {"acme": other}) is False


def test_hmac_and_ed25519_coexist_in_one_keyring() -> None:
    from volo_core import generate_keypair

    priv, pub = generate_keypair()
    hmac_pack = sign_pack(_pack("h"), publisher="team", secret="s3cret")
    ed_pack = sign_pack_ed25519(_pack("e"), publisher="pub", private_pem=priv)
    keyring = {"team": "s3cret", "pub": pub}
    assert verify_pack_signature(hmac_pack, keyring) is True
    assert verify_pack_signature(ed_pack, keyring) is True
