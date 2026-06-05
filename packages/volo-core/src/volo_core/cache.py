"""Canonical request normalization for deterministic cache keys (bible §9.2 Tier-1).

Two requests with the same logical content should hash identically regardless of dict ordering,
incidental whitespace, or Python int-vs-float boundaries. This module is the single source of
truth for that normalization so the Recorder, the Replayer, and the cache layer agree.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_json(value: Any) -> str:
    """Return a stable JSON string with sorted keys, no whitespace, ints over float-equivalents."""
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"))


def cache_key(*parts: Any) -> str:
    """A short content-addressed key for a model or tool request.

    The key is the BLAKE2b-128 digest of the canonical JSON of the parts joined by ``\\x1f`` —
    short enough to log, collision-resistant, and stable across Python versions.
    """
    blob = "\x1f".join(canonical_json(p) for p in parts).encode("utf-8")
    return hashlib.blake2b(blob, digest_size=16).hexdigest()
