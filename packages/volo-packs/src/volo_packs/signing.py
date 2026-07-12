"""Pack signing — publisher signatures + keyring verification (newplan M25 / ADR-0028).

A signature binds a pack's **identity** (`name@version`) to its **content checksum** under a
publisher's key, so install can trust that a pack came from who the registry says and wasn't
altered. The v1 algorithm is HMAC-SHA256 (stdlib, no dependency): a shared-secret scheme suited
to private/team registries. The signature envelope is algorithm-tagged so an asymmetric upgrade
(Ed25519) can be added later without a format change — see ADR-0028.

A ``Keyring`` maps ``publisher → secret``. The signer holds their secret; a verifier holds the
keyring of publishers it trusts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from volo_core import ED25519, sign_ed25519, verify_ed25519
from volo_packs.pack import Pack, PackSignature, content_checksum

HMAC_SHA256 = "hmac-sha256"

# A keyring maps publisher -> secret (HMAC) or public-key PEM (Ed25519); the branch is chosen by
# the signature's algorithm tag, so a registry can mix symmetric and asymmetric publishers.
Keyring = dict[str, str]


def _message(pack: Pack) -> bytes:
    """The signed bytes: identity + content checksum (binds both)."""
    m = pack.manifest
    return f"{m.name}@{m.version}:{m.checksum}".encode()


def sign_pack(pack: Pack, *, publisher: str, secret: str) -> Pack:
    """Sign ``pack`` in place with ``publisher``'s ``secret``; returns the pack."""
    if not publisher:
        raise ValueError("publisher is required to sign a pack")
    value = hmac.new(secret.encode("utf-8"), _message(pack), hashlib.sha256).hexdigest()
    pack.manifest.signature = PackSignature(publisher=publisher, algorithm=HMAC_SHA256, value=value)
    return pack


def sign_pack_ed25519(pack: Pack, *, publisher: str, private_pem: str) -> Pack:
    """Sign ``pack`` with ``publisher``'s Ed25519 private key (asymmetric); returns the pack."""
    if not publisher:
        raise ValueError("publisher is required to sign a pack")
    value = sign_ed25519(_message(pack), private_pem)
    pack.manifest.signature = PackSignature(publisher=publisher, algorithm=ED25519, value=value)
    return pack


def verify_pack_signature(pack: Pack, keyring: Keyring) -> bool:
    """True if the pack carries a valid signature from a keyring publisher over its **actual** content.

    The signed message binds the manifest checksum, so verification first confirms the manifest
    checksum still matches the real items — otherwise an attacker could swap ``pack.items`` while
    leaving ``manifest.checksum`` (and thus the signature) untouched and still verify as valid.
    Handles both HMAC (keyring value = shared secret) and Ed25519 (keyring value = public-key PEM),
    selected by the signature's algorithm tag.
    """
    sig = pack.manifest.signature
    if sig is None:
        return False
    # Re-bind to real content: a stale/forged manifest checksum invalidates the signature.
    if content_checksum(pack.items) != pack.manifest.checksum:
        return False
    key = keyring.get(sig.publisher)
    if key is None:
        return False
    if sig.algorithm == HMAC_SHA256:
        expected = hmac.new(key.encode("utf-8"), _message(pack), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig.value)
    if sig.algorithm == ED25519:
        return verify_ed25519(_message(pack), sig.value, key)
    return False


def load_keyring(path: Path | str) -> Keyring:
    """Load a ``{publisher: secret}`` keyring from JSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("keyring must be a JSON object of publisher -> secret")
    return {str(k): str(v) for k, v in raw.items()}
