"""RS256 / JWKS SSO: asymmetric JWT verification against a published public JWKS."""

from __future__ import annotations

import json

import pytest
import volo_cloud.app as cloud_app
from fastapi.testclient import TestClient
from volo_cloud import rbac
from volo_cloud.rbac import (
    AccessDenied,
    generate_rsa_jwks,
    mint_rs256_jwt,
    token_alg,
    verify_rs256_jwt,
)


def test_rs256_roundtrip_with_jwks() -> None:
    priv, jwks = generate_rsa_jwks()
    tok = mint_rs256_jwt(subject="user-1", private_key=priv, issuer="idp", audience="volo")
    assert token_alg(tok) == "RS256"
    assert verify_rs256_jwt(tok, jwks=jwks, issuer="idp", audience="volo") == "user-1"


def test_rs256_rejects_wrong_key_tamper_and_claims() -> None:
    priv, _ = generate_rsa_jwks()
    _, other_jwks = generate_rsa_jwks()  # a different keypair's public JWKS
    tok = mint_rs256_jwt(subject="u", private_key=priv, issuer="idp", audience="volo")
    with pytest.raises(AccessDenied, match=r"signature|kid"):
        verify_rs256_jwt(tok, jwks=other_jwks, issuer="idp", audience="volo")
    _, jwks = generate_rsa_jwks()
    with pytest.raises(AccessDenied):  # wrong issuer (and wrong key)
        verify_rs256_jwt(tok, jwks=jwks, issuer="other", audience="volo")


def test_expired_rs256_rejected() -> None:
    priv, jwks = generate_rsa_jwks()
    tok = mint_rs256_jwt(subject="u", private_key=priv, ttl_s=-1)
    with pytest.raises(AccessDenied, match=r"expired|signature"):
        verify_rs256_jwt(tok, jwks=jwks, issuer=None, audience=None)


def test_jwt_principal_dispatches_rs256(monkeypatch: pytest.MonkeyPatch) -> None:
    priv, jwks = generate_rsa_jwks()
    monkeypatch.delenv("VOLO_JWT_SECRET", raising=False)
    monkeypatch.delenv("VOLO_JWT_ISS", raising=False)
    monkeypatch.delenv("VOLO_JWT_AUD", raising=False)
    monkeypatch.setenv("VOLO_JWT_JWKS", json.dumps(jwks))
    tok = mint_rs256_jwt(subject="user-42", private_key=priv)
    p = rbac.jwt_principal(f"Bearer {tok}")
    assert not p.is_anonymous and p.subject == "user-42"


def test_hs256_and_rs256_coexist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both verifiers configured; the token's own alg picks the path."""
    priv, jwks = generate_rsa_jwks()
    monkeypatch.setenv("VOLO_JWT_SECRET", "s3cret")
    monkeypatch.setenv("VOLO_JWT_JWKS", json.dumps(jwks))
    monkeypatch.delenv("VOLO_JWT_ISS", raising=False)
    monkeypatch.delenv("VOLO_JWT_AUD", raising=False)
    hs = rbac.mint_hs256_jwt(subject="hs-user", secret="s3cret")
    rs = mint_rs256_jwt(subject="rs-user", private_key=priv)
    assert rbac.jwt_principal(f"Bearer {hs}").subject == "hs-user"
    assert rbac.jwt_principal(f"Bearer {rs}").subject == "rs-user"


def test_no_config_is_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOLO_JWT_SECRET", raising=False)
    monkeypatch.delenv("VOLO_JWT_JWKS", raising=False)
    assert rbac.jwt_principal("Bearer whatever").is_anonymous


def test_rs256_enforced_over_the_api(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    priv, jwks = generate_rsa_jwks()
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'rs.db').as_posix()}")
    monkeypatch.setattr(cloud_app, "_engine", None)
    monkeypatch.setenv("VOLO_JWT_JWKS", json.dumps(jwks))
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    client = TestClient(cloud_app.create_cloud_app())

    # no token -> 401 under require-auth
    assert client.post("/cloud/teams", json={"slug": "t", "name": "T"}).status_code == 401
    # a valid RS256 token authenticates and creates a team (becoming its owner)
    tok = mint_rs256_jwt(subject="owner-1", private_key=priv)
    r = client.post(
        "/cloud/teams", json={"slug": "t", "name": "T"}, headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 200, r.text
