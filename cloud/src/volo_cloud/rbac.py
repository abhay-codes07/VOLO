"""RBAC + a vendor-neutral SSO seam (M30). Commercial — see cloud/LICENSE.

**Roles.** A ``Membership`` carries a role (``owner`` > ``admin`` > ``member``); ``require_role``
enforces a minimum on a team. Role changes and membership are audited.

**SSO.** ``jwt_principal`` verifies a bearer JWT issued by *any* vendor (Clerk, Supabase, Auth0,
Okta, Cognito, …). Two algorithms are supported and selected by the token's own ``alg`` header:
**HS256** (shared secret via ``VOLO_JWT_SECRET``, stdlib) and **RS256** (asymmetric, verified
against a published ``VOLO_JWT_JWKS`` document — the mode most IdPs use). ``VOLO_JWT_ISS`` /
``VOLO_JWT_AUD`` add issuer/audience checks. With neither secret nor JWKS set it returns the OSS
anonymous principal, so local dev needs nothing. RS256 needs the ``cryptography`` dependency
(ADR-0035).
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


def _split(token: str) -> tuple[str, str, str]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as exc:
        raise AccessDenied("malformed JWT") from exc
    return header_b64, payload_b64, sig_b64


def _validate_claims(payload_b64: str, *, issuer: str | None, audience: str | None) -> str:
    """Check exp / iss / aud and return the subject. Raises ``AccessDenied`` on any failure."""
    claims = json.loads(_b64url_decode(payload_b64))
    exp = claims.get("exp")
    # Require exp: a token without an expiry never expires, and JWTs have no revocation, so a
    # captured no-exp token would be a permanent credential.
    if not isinstance(exp, int | float):
        raise AccessDenied("JWT missing 'exp'")
    if time.time() > exp:
        raise AccessDenied("JWT expired")
    if issuer and claims.get("iss") != issuer:
        raise AccessDenied("JWT issuer mismatch")
    if audience and claims.get("aud") != audience:
        raise AccessDenied("JWT audience mismatch")
    sub = claims.get("sub")
    if not sub:
        raise AccessDenied("JWT missing 'sub'")
    return str(sub)


def token_alg(token: str) -> str:
    """Peek at a JWT's declared algorithm without verifying it."""
    header_b64, _, _ = _split(token)
    return str(json.loads(_b64url_decode(header_b64)).get("alg", ""))


def verify_hs256_jwt(token: str, *, secret: str, issuer: str | None, audience: str | None) -> str:
    """Verify an HS256 JWT and return its subject. Raises ``AccessDenied`` on any failure."""
    header_b64, payload_b64, sig_b64 = _split(token)
    header = json.loads(_b64url_decode(header_b64))
    if header.get("alg") != "HS256":
        raise AccessDenied(f"unsupported JWT alg {header.get('alg')!r} (only HS256)")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise AccessDenied("bad JWT signature")
    return _validate_claims(payload_b64, issuer=issuer, audience=audience)


# ── SSO (RS256 / JWKS, asymmetric — needs `cryptography`) ─────────────────────


def _rsa() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise AccessDenied("RS256 JWT verification needs the 'cryptography' package") from exc
    return hashes, padding, rsa, InvalidSignature


def _b64url_uint(val: str) -> int:
    return int.from_bytes(_b64url_decode(val), "big")


def _public_key_from_jwk(jwk: dict[str, Any]):  # type: ignore[no-untyped-def]
    """Build an RSA public key from an RFC 7517 JWK (n, e)."""
    _, _, rsa, _ = _rsa()
    if jwk.get("kty") != "RSA":
        raise AccessDenied(f"unsupported JWK kty {jwk.get('kty')!r} (only RSA)")
    numbers = rsa.RSAPublicNumbers(_b64url_uint(jwk["e"]), _b64url_uint(jwk["n"]))
    return numbers.public_key()


def _select_jwk(jwks: dict[str, Any], kid: str | None) -> dict[str, Any]:
    keys = jwks.get("keys", [])
    if not keys:
        raise AccessDenied("JWKS has no keys")
    if kid is not None:
        for k in keys:
            if k.get("kid") == kid:
                return dict(k)
        raise AccessDenied(f"no JWKS key matches kid {kid!r}")
    return dict(keys[0])  # single-key JWKS: no kid required


def verify_rs256_jwt(
    token: str, *, jwks: dict[str, Any], issuer: str | None, audience: str | None
) -> str:
    """Verify an RS256 JWT against a JWKS (public keys) and return its subject."""
    hashes, padding, _, invalid_signature = _rsa()
    header_b64, payload_b64, sig_b64 = _split(token)
    header = json.loads(_b64url_decode(header_b64))
    if header.get("alg") != "RS256":
        raise AccessDenied(f"unsupported JWT alg {header.get('alg')!r} (expected RS256)")
    public_key = _public_key_from_jwk(_select_jwk(jwks, header.get("kid")))
    signing_input = f"{header_b64}.{payload_b64}".encode()
    try:
        public_key.verify(
            _b64url_decode(sig_b64), signing_input, padding.PKCS1v15(), hashes.SHA256()
        )
    except invalid_signature as exc:
        raise AccessDenied("bad JWT signature") from exc
    return _validate_claims(payload_b64, issuer=issuer, audience=audience)


def jwt_principal(authorization: str | None) -> Principal:
    """Resolve a Principal from an ``Authorization: Bearer <jwt>`` header (vendor-neutral SSO).

    Configured by env: ``VOLO_JWT_SECRET`` enables **HS256** (shared secret) and ``VOLO_JWT_JWKS``
    (a JSON JWKS document) enables **RS256** (asymmetric — the mode real IdPs like Auth0/Okta/
    Cognito use, publishing their public keys as a JWKS). The token's own ``alg`` header selects
    which verifier runs. With neither configured → OSS anonymous principal (local dev). A present
    but invalid token raises ``AccessDenied``.
    """
    secret = os.environ.get("VOLO_JWT_SECRET")
    jwks_raw = os.environ.get("VOLO_JWT_JWKS")
    if not secret and not jwks_raw:
        return Principal.anonymous()
    if not authorization or not authorization.lower().startswith("bearer "):
        return Principal.anonymous()
    token = authorization.split(" ", 1)[1].strip()
    issuer, audience = os.environ.get("VOLO_JWT_ISS"), os.environ.get("VOLO_JWT_AUD")
    alg = token_alg(token)
    if alg == "HS256" and secret:
        sub = verify_hs256_jwt(token, secret=secret, issuer=issuer, audience=audience)
    elif alg == "RS256" and jwks_raw:
        sub = verify_rs256_jwt(token, jwks=json.loads(jwks_raw), issuer=issuer, audience=audience)
    else:
        raise AccessDenied(
            f"JWT alg {alg!r} is not configured (set VOLO_JWT_SECRET or VOLO_JWT_JWKS)"
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


def _seg(obj: dict[str, Any]) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )


def _uint_b64url(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def generate_rsa_jwks(kid: str = "k1") -> tuple[Any, dict[str, Any]]:
    """Generate an RSA keypair; return ``(private_key, jwks)`` — for local issuance and tests.

    In production the JWKS comes from the IdP's published endpoint; Volo only holds the public JWKS.
    """
    _, _, rsa, _ = _rsa()
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": _uint_b64url(pub.n),
        "e": _uint_b64url(pub.e),
    }
    return priv, {"keys": [jwk]}


def mint_rs256_jwt(
    *,
    subject: str,
    private_key: Any,
    kid: str = "k1",
    issuer: str | None = None,
    audience: str | None = None,
    ttl_s: int = 3600,
) -> str:
    """Mint an RS256 JWT signed by ``private_key`` — for tests / local issuance."""
    hashes, padding, _, _ = _rsa()
    header = _seg({"alg": "RS256", "typ": "JWT", "kid": kid})
    claims: dict[str, Any] = {"sub": subject, "exp": int(time.time()) + ttl_s}
    if issuer:
        claims["iss"] = issuer
    if audience:
        claims["aud"] = audience
    payload = _seg(claims)
    sig = private_key.sign(f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{payload}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"
