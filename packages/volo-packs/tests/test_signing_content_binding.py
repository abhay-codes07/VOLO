"""Regression: a signature must not verify once the pack's actual content is tampered."""

from __future__ import annotations

from volo_packs import build_pack, sign_pack, starter_items, verify_pack_signature
from volo_packs.pack import Pack


def _signed() -> Pack:
    pack = build_pack(name="p", version="1.0.0", kind="attacks", items=starter_items("attacks"))
    sign_pack(pack, publisher="acme", secret="s3cret")
    return pack


def test_untampered_pack_verifies() -> None:
    assert verify_pack_signature(_signed(), {"acme": "s3cret"}) is True


def test_content_tamper_invalidates_signature() -> None:
    pack = _signed()
    # swap the payload but leave manifest.checksum (and thus the HMAC) untouched
    pack.items.append(
        {"id": "evil", "category": "x", "technique": "pwn", "payload": "rm -rf /",
         "expected_behavior": "refuse"}
    )
    assert verify_pack_signature(pack, {"acme": "s3cret"}) is False


def test_manifest_checksum_forgery_invalidates_signature() -> None:
    pack = _signed()
    pack.items.clear()
    pack.manifest.checksum = "deadbeef"  # forged to match nothing real
    assert verify_pack_signature(pack, {"acme": "s3cret"}) is False
