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

from volo_packs.pack import Pack, PackSignature, content_checksum

HMAC_SHA256 = "hmac-sha256"

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


def verify_pack_signature(pack: Pack, keyring: Keyring) -> bool:
    """True if the pack carries a signature from a keyring publisher over its current content."""
    sig = pack.manifest.signature
    if sig is None or sig.algorithm != HMAC_SHA256:
        return False
    secret = keyring.get(sig.publisher)
    if secret is None:
        return False
    # Verify the manifest's checksum matches actual content before trusting signature.
    actual_checksum = content_checksum(pack.items)
    if not hmac.compare_digest(actual_checksum, pack.manifest.checksum):
        return False
    expected = hmac.new(secret.encode("utf-8"), _message(pack), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig.value)


def load_keyring(path: Path | str) -> Keyring:
    """Load a ``{publisher: secret}`` keyring from JSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("keyring must be a JSON object of publisher -> secret")
    return {str(k): str(v) for k, v in raw.items()}
