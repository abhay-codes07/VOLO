"""M30: RBAC roles, vendor-neutral HS256 JWT SSO, and the audit log."""

from __future__ import annotations

from pathlib import Path

import pytest
import volo_cloud.app as cloud_app
from fastapi.testclient import TestClient
from volo_cloud import audit, rbac, service
from volo_cloud.rbac import AccessDenied, mint_hs256_jwt, verify_hs256_jwt

from volo_core.storage import get_engine, init_schema


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VOLO_DB_URL", f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    monkeypatch.setattr(cloud_app, "_engine", None)
    eng = get_engine()
    init_schema(eng)
    return eng


# ── RBAC ──────────────────────────────────────────────────────────────────────


def test_roles_rank_and_require(engine) -> None:
    team = service.create_team(engine, slug="t", name="T", owner="alice")
    assert rbac.role_on_team(engine, subject="alice", team_id=team.id) == "owner"
    assert rbac.has_role(engine, subject="alice", team_id=team.id, minimum="admin")
    # a non-member has no role
    assert not rbac.has_role(engine, subject="bob", team_id=team.id, minimum="member")
    with pytest.raises(AccessDenied):
        rbac.require_role(engine, subject="bob", team_id=team.id, minimum="member")


def test_set_member_role(engine) -> None:
    team = service.create_team(engine, slug="t", name="T", owner="alice")
    rbac.set_member_role(engine, team_id=team.id, subject="bob", role="admin")
    assert rbac.has_role(engine, subject="bob", team_id=team.id, minimum="admin")
    assert not rbac.has_role(engine, subject="bob", team_id=team.id, minimum="owner")
    with pytest.raises(ValueError, match="unknown role"):
        rbac.set_member_role(engine, team_id=team.id, subject="x", role="wizard")


# ── SSO (HS256 JWT) ───────────────────────────────────────────────────────────


def test_jwt_roundtrip_and_tampering() -> None:
    tok = mint_hs256_jwt(subject="user-1", secret="s3cret", issuer="volo", audience="cloud")
    assert verify_hs256_jwt(tok, secret="s3cret", issuer="volo", audience="cloud") == "user-1"
    with pytest.raises(AccessDenied):
        verify_hs256_jwt(tok, secret="wrong", issuer="volo", audience="cloud")
    with pytest.raises(AccessDenied, match="issuer"):
        verify_hs256_jwt(tok, secret="s3cret", issuer="other", audience="cloud")


def test_expired_jwt_rejected() -> None:
    tok = mint_hs256_jwt(subject="u", secret="s", ttl_s=-1)
    with pytest.raises(AccessDenied, match="expired"):
        verify_hs256_jwt(tok, secret="s", issuer=None, audience=None)


def test_jwt_principal_anonymous_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOLO_JWT_SECRET", raising=False)
    assert rbac.jwt_principal("Bearer whatever").is_anonymous


def test_jwt_principal_authenticates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_JWT_SECRET", "s3cret")
    monkeypatch.delenv("VOLO_JWT_ISS", raising=False)
    monkeypatch.delenv("VOLO_JWT_AUD", raising=False)
    tok = mint_hs256_jwt(subject="user-42", secret="s3cret")
    p = rbac.jwt_principal(f"Bearer {tok}")
    assert not p.is_anonymous and p.subject == "user-42"


# ── audit ─────────────────────────────────────────────────────────────────────


def test_audit_record_and_list(engine) -> None:
    audit.record_audit(engine, subject="alice", action="team.create", target="team:1", team_id=1)
    audit.record_audit(engine, subject="alice", action="quota.set", target="workspace:2", team_id=1)
    rows = audit.list_audit(engine, team_id=1)
    assert {r.action for r in rows} == {"team.create", "quota.set"}
    assert audit.list_audit(engine, team_id=999) == []


# ── over the API: JWT auth + role enforcement + audit trail ───────────────────


def test_api_rbac_enforced_and_audited(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_JWT_SECRET", "s3cret")
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    client = TestClient(cloud_app.create_cloud_app())

    owner = mint_hs256_jwt(subject="owner-1", secret="s3cret")
    outsider = mint_hs256_jwt(subject="outsider", secret="s3cret")

    # no token → 401 under require-auth
    assert client.post("/cloud/teams", json={"slug": "t", "name": "T"}).status_code == 401

    # owner creates a team (becomes owner) and a workspace
    oh = {"Authorization": f"Bearer {owner}"}
    team = client.post("/cloud/teams", json={"slug": "t", "name": "T"}, headers=oh).json()
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces", json={"slug": "w", "name": "W"}, headers=oh
    )
    assert ws.status_code == 200, ws.text

    # an outsider (no role on the team) is denied 403
    denied = client.post(
        f"/cloud/teams/{team['id']}/workspaces",
        json={"slug": "w2", "name": "W2"},
        headers={"Authorization": f"Bearer {outsider}"},
    )
    assert denied.status_code == 403

    # the mutations are on the audit trail (owner can read it)
    trail = client.get(f"/cloud/teams/{team['id']}/audit", headers=oh).json()
    actions = {e["action"] for e in trail}
    assert "team.create" in actions and "workspace.create" in actions


def test_owner_can_grant_roles_over_api(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLO_JWT_SECRET", "s3cret")
    monkeypatch.setenv("VOLO_REQUIRE_AUTH", "true")
    client = TestClient(cloud_app.create_cloud_app())
    owner = mint_hs256_jwt(subject="owner-1", secret="s3cret")
    oh = {"Authorization": f"Bearer {owner}"}
    team = client.post("/cloud/teams", json={"slug": "t", "name": "T"}, headers=oh).json()

    # grant 'bob' admin
    r = client.post(
        f"/cloud/teams/{team['id']}/members", json={"subject": "bob", "role": "admin"}, headers=oh
    )
    assert r.status_code == 200 and r.json()["role"] == "admin"

    # now bob can create a workspace
    bob = mint_hs256_jwt(subject="bob", secret="s3cret")
    ws = client.post(
        f"/cloud/teams/{team['id']}/workspaces",
        json={"slug": "w", "name": "W"},
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert ws.status_code == 200, ws.text
