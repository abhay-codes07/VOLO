"""RBAC + a vendor-neutral SSO seam (M30). Commercial — see cloud/LICENSE.

**Roles.** A ``Membership`` carries a role (``owner`` > ``admin`` > ``member``); ``require_role``
enforces a minimum on a team. Role changes and membership are audited.

**SSO.** ``jwt_principal`` verifies a bearer JWT (HS256, stdlib — no crypto dependency) issued by
*any* vendor (Clerk, Supabase, Auth0, …) configured via ``VOLO_JWT_SECRET`` / ``VOLO_JWT_ISS`` /
``VOLO_JWT_AUD``. When no secret is set it returns the OSS anonymous principal, so local dev needs
nothing. RS256/JWKS (asymmetric) is the documented upgrade — it needs a crypto dependency (ADR-0034).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from volo_api.auth import Principal
from volo_cloud.models import Membership

_ROLE_RANK: dict[str, int] = {"member": 0, "admin": 1, "owner": 2}


class AccessDenied(RuntimeError):
    """Raised when a subject lacks the required role on a team."""


# ── RBAC ─────────────────────────────────────────────────────────────────────


def role_on_team(engine: Engine, *, subject: str, team_id: int) -> str | None:
    with Session(engine) as s:
        m = s.exec(
            select(Membership).where(Membership.team_id == team_id, Membership.subject == subject)
        ).first()
        return m.role if m is not None else None


def has_role(engine: Engine, *, subject: str, team_id: int, minimum: str) -> bool:
    role = role_on_team(engine, subject=subject, team_id=team_id)
    if role is None:
        return False
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK.get(minimum, 99)


def require_role(engine: Engine, *, subject: str, team_id: int, minimum: str) -> None:
    if not has_role(engine, subject=subject, team_id=team_id, minimum=minimum):
        raise AccessDenied(f"subject {subject!r} needs role >= {minimum!r} on team {team_id}")


def set_member_role(engine: Engine, *, team_id: int, subject: str, role: str) -> Membership:
    if role not in _ROLE_RANK:
        raise ValueError(f"unknown role {role!r}; known: {sorted(_ROLE_RANK)}")
    with Session(engine, expire_on_commit=False) as s:
        m = s.exec(
            select(Membership).where(Membership.team_id == team_id, Membership.subject == subject)
        ).first()
        if m is None:
            m = Membership(team_id=team_id, subject=subject, role=role)
        else:
            m.role = role
        s.add(m)
        s.commit()
        s.refresh(m)
        return m


# ── SSO (HS256 JWT, stdlib) ──────────────────────────────────────────────────


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def verify_hs256_jwt(token: str, *, secret: str, issuer: str | None, audience: str | None) -> str:
    """Verify an HS256 JWT and return its subject. Raises ``AccessDenied`` on any failure."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as exc:
        raise AccessDenied("malformed JWT") from exc
    header = json.loads(_b64url_decode(header_b64))
    if header.get("alg") != "HS256":
        raise AccessDenied(f"unsupported JWT alg {header.get('alg')!r} (only HS256)")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise AccessDenied("bad JWT signature")
    claims = json.loads(_b64url_decode(payload_b64))
    exp = claims.get("exp")
    if isinstance(exp, int | float) and time.time() > exp:
        raise AccessDenied("JWT expired")
    if issuer and claims.get("iss") != issuer:
        raise AccessDenied("JWT issuer mismatch")
    if audience and claims.get("aud") != audience:
        raise AccessDenied("JWT audience mismatch")
    sub = claims.get("sub")
    if not sub:
        raise AccessDenied("JWT missing 'sub'")
    return str(sub)


def jwt_principal(authorization: str | None) -> Principal:
    """Resolve a Principal from an ``Authorization: Bearer <jwt>`` header (vendor-neutral SSO).

    No ``VOLO_JWT_SECRET`` → OSS anonymous principal (local dev). With a secret set, a valid HS256
    token yields an authenticated principal; an invalid one raises ``AccessDenied``.
    """
    secret = os.environ.get("VOLO_JWT_SECRET")
    if not secret:
        return Principal.anonymous()
    if not authorization or not authorization.lower().startswith("bearer "):
        return Principal.anonymous()
    token = authorization.split(" ", 1)[1].strip()
    sub = verify_hs256_jwt(
        token,
        secret=secret,
        issuer=os.environ.get("VOLO_JWT_ISS"),
        audience=os.environ.get("VOLO_JWT_AUD"),
    )
    return Principal(subject=sub, is_anonymous=False)


def mint_hs256_jwt(
    *,
    subject: str,
    secret: str,
    issuer: str | None = None,
    audience: str | None = None,
    ttl_s: int = 3600,
) -> str:
    """Mint an HS256 JWT — for tests and for local issuance; production tokens come from the vendor."""

    def _seg(obj: dict[str, Any]) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )

    header = _seg({"alg": "HS256", "typ": "JWT"})
    claims: dict[str, Any] = {"sub": subject, "exp": int(time.time()) + ttl_s}
    if issuer:
        claims["iss"] = issuer
    if audience:
        claims["aud"] = audience
    payload = _seg(claims)
    sig = hmac.new(secret.encode("utf-8"), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig_b64}"
