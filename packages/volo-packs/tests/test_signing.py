"""Pack signing: HMAC signature binds identity+content; verify against a keyring."""

from __future__ import annotations

import json
from pathlib import Path

from volo_packs import (
    build_pack,
    load_keyring,
    sign_pack,
    starter_items,
    verify_pack_signature,
)


def _pack(version: str = "1.0.0"):
    return build_pack(name="acme", version=version, kind="attacks", items=starter_items("attacks"))


def test_sign_then_verify_roundtrip() -> None:
    pack = sign_pack(_pack(), publisher="acme", secret="s3cret")
    assert pack.manifest.signature is not None
    assert pack.manifest.signature.publisher == "acme"
    assert verify_pack_signature(pack, {"acme": "s3cret"}) is True


def test_wrong_secret_fails() -> None:
    pack = sign_pack(_pack(), publisher="acme", secret="s3cret")
    assert verify_pack_signature(pack, {"acme": "wrong"}) is False


def test_unknown_publisher_fails() -> None:
    pack = sign_pack(_pack(), publisher="acme", secret="s3cret")
    assert verify_pack_signature(pack, {"other": "s3cret"}) is False


def test_unsigned_pack_never_verifies() -> None:
    assert verify_pack_signature(_pack(), {"acme": "s3cret"}) is False


def test_tampering_content_breaks_signature() -> None:
    pack = sign_pack(_pack(), publisher="acme", secret="s3cret")
    # alter items after signing → checksum in the signed message no longer matches
    pack.manifest.checksum = "0" * 64
    assert verify_pack_signature(pack, {"acme": "s3cret"}) is False


def test_signature_binds_version() -> None:
    # a signature for 1.0.0 must not verify if the manifest version is swapped to 2.0.0
    pack = sign_pack(_pack(version="1.0.0"), publisher="acme", secret="s3cret")
    pack.manifest.version = "2.0.0"
    assert verify_pack_signature(pack, {"acme": "s3cret"}) is False


def test_load_keyring(tmp_path: Path) -> None:
    path = tmp_path / "keyring.json"
    path.write_text(json.dumps({"acme": "s3cret", "beta": "k2"}), encoding="utf-8")
    assert load_keyring(path) == {"acme": "s3cret", "beta": "k2"}
