# ADR 0035: RBAC via team roles, vendor-neutral HS256-JWT SSO, append-only audit

- Status: accepted
- Date: 2026-07-08

## Context

M30 adds the enterprise checklist to the commercial control plane (ADR-0031): role-based access
control, single sign-on, and an audit trail. The bible (§0) requires sign-off before a paid
dependency, and (§11) that everything still runs locally with zero accounts — so SSO cannot hard-
require a specific paid vendor or a crypto library.

## Decision

1. **RBAC is team roles with a rank.** `Membership.role` is `owner > admin > member`;
   `require_role(minimum)` enforces a floor. Management mutations (create workspace/key, set quota)
   require `admin`; granting roles requires `owner`. A team's creator is its `owner`, so in local
   **anonymous** mode the anonymous subject owns the teams it created and every check passes —
   zero-config dev is unchanged, and the moment real identities exist the same checks bind.
2. **SSO is vendor-neutral HS256 JWT, stdlib only.** `jwt_principal` verifies an
   `Authorization: Bearer <jwt>` token with `hmac` (no crypto dependency), configured via
   `VOLO_JWT_SECRET` / `VOLO_JWT_ISS` / `VOLO_JWT_AUD`. Any provider that issues HS256 tokens
   (Clerk, Supabase, Auth0, an in-house IdP) works — Volo isn't coupled to one vendor. With no
   secret set it returns the OSS anonymous principal, preserving local-first. **RS256/JWKS**
   (asymmetric, the common production mode) is the documented upgrade and is gated on adding a
   vetted crypto dependency with founder approval — the verifier is structured so that's a new
   `alg` branch, not a rewrite.
3. **Audit is append-only.** Every management mutation writes an `AuditEvent`
   `(subject, action, target, team_id, at)`; there is no update/delete API, so the log can back a
   compliance trail (feeds M29 evidence). `GET /cloud/teams/{id}/audit` returns it (member+).

## Consequences

- The whole enterprise tier is exercisable locally with `uv run` + SQLite and a self-minted test
  token (`mint_hs256_jwt`), so RBAC/SSO/audit are developed and tested with no vendor and no infra
  — consistent with §11 and ADR-0031.
- HS256 is symmetric: the verifier holds the same secret the IdP signs with. That's fine for a
  single-tenant deployment or a trusted IdP integration; multi-issuer public verification wants
  RS256/JWKS (the documented next step). Stated plainly rather than implied.
- Because anonymous owns its own teams, turning `VOLO_REQUIRE_AUTH` on (and a JWT secret) flips the
  same code from open-local to enforced-cloud with no route changes — the seam ADR-0031 promised.
- Roles are team-scoped (not workspace-scoped) for the MVP; finer-grained per-workspace roles are
  an additive change behind `require_role`.

## Alternatives considered

- **Adopt a specific auth vendor SDK (Clerk/Supabase)** — rejected: a paid dependency and vendor
  lock-in for what a standard JWT verify handles; the env-configured HS256 seam accepts any of them.
- **RS256 now via `cryptography`/PyJWT** — deferred: needs founder sign-off for the dependency;
  HS256 ships the capability today and the upgrade is a localized change.
- **Mutable audit rows / a generic event table** — rejected: append-only is the property that
  makes an audit log trustworthy; a dedicated table with no mutation API enforces it.
