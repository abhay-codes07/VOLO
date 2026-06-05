"""Pluggable auth seam (bible §9.6).

OSS mode: no auth — every request gets the ``Principal.anonymous()`` sentinel.

Cloud mode: swap ``get_principal`` for a real verifier (Clerk session, Supabase JWT, etc.).
The seam is a FastAPI ``Depends`` so callers don't change.

State-mutating routes additionally depend on ``require_principal``, which **denies** anonymous
callers when ``VOLO_REQUIRE_AUTH=true`` (the posture for any non-localhost deployment). The OSS
default leaves it off so local use needs no setup. See ADR-0012.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException


@dataclass(frozen=True)
class Principal:
    """Authenticated identity. ``is_anonymous=True`` in OSS mode."""

    subject: str
    is_anonymous: bool = False

    @classmethod
    def anonymous(cls) -> Principal:
        return cls(subject="anonymous", is_anonymous=True)


def get_principal() -> Principal:
    """Default FastAPI dependency — returns the OSS anonymous principal.

    Cloud overrides this in ``services/cloud/auth.py`` (when the cloud/ dir lands).
    """
    return Principal.anonymous()


def auth_required() -> bool:
    """Whether anonymous access is forbidden — true iff ``VOLO_REQUIRE_AUTH=true``."""
    return os.environ.get("VOLO_REQUIRE_AUTH", "false").lower() == "true"


def require_principal(principal: Principal = Depends(get_principal)) -> Principal:
    """Dependency for state-mutating routes: 401 anonymous callers when auth is required.

    No-op in OSS local mode (``VOLO_REQUIRE_AUTH`` unset), so existing workflows are unchanged;
    a deployment sets the flag and swaps ``get_principal`` for a real verifier.
    """
    if auth_required() and principal.is_anonymous:
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


__all__ = ["Principal", "auth_required", "get_principal", "require_principal"]
