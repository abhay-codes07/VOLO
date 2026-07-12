"""A JWT without an `exp` claim must be rejected (no permanent credentials)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from volo_cloud.rbac import AccessDenied, mint_hs256_jwt, verify_hs256_jwt


def _mint_without_exp(subject: str, secret: str) -> str:
    def seg(obj: dict[str, object]) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )

    header = seg({"alg": "HS256", "typ": "JWT"})
    payload = seg({"sub": subject})  # deliberately no 'exp'
    sig = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


def test_token_without_exp_is_rejected() -> None:
    tok = _mint_without_exp("user-1", "s3cret")  # validly signed, but no expiry
    with pytest.raises(AccessDenied, match="missing 'exp'"):
        verify_hs256_jwt(tok, secret="s3cret", issuer=None, audience=None)


def test_normal_token_with_exp_still_verifies() -> None:
    tok = mint_hs256_jwt(subject="user-1", secret="s3cret")  # always sets exp
    assert verify_hs256_jwt(tok, secret="s3cret", issuer=None, audience=None) == "user-1"


def test_expired_token_still_rejected() -> None:
    tok = mint_hs256_jwt(subject="u", secret="s", ttl_s=-1)
    with pytest.raises(AccessDenied, match="expired"):
        verify_hs256_jwt(tok, secret="s", issuer=None, audience=None)
