# ADR 0031: the cloud control plane is a commercial `cloud/` dir; API-key auth, runs locally on SQLite

- Status: accepted
- Date: 2026-07-08

## Context

M26 opens wave 4's paid tier: a hosted control plane (teams, workspaces, report history). ADR-0001
already fixed the open-core boundary (Apache-2.0 core + a separate commercial `cloud/`); the
founder authorized building it. Two constraints from the bible stay binding: everything must run
**locally with zero cloud accounts** (§11), and adding a paid dependency needs sign-off (§0).

## Decision

1. **Commercial code lives in `cloud/` with its own license.** `cloud/LICENSE` is a commercial
   license; `cloud/pyproject.toml` declares `LicenseRef-Volo-Commercial`. The OSS engine
   (`packages/`, `services/api`, `apps/web`, `integrations/`) stays Apache-2.0 and imports nothing
   from `cloud/`. `cloud/` is a workspace member so it builds and is tested, but it is a distinct
   licensing island.
2. **No paid dependency; the stack is what's already here.** FastAPI + SQLModel + the existing
   `volo_core.storage` engine factory. It runs on **SQLite locally** (zero accounts) and Postgres
   in production purely via `VOLO_DB_URL` — no code change. Cloud tables are prefixed `cloud_*` so
   they coexist with the OSS schema on one engine.
3. **Two-layer auth, both pluggable.** *Data* routes (read/ingest a workspace's reports) require a
   workspace **API key** via `X-Volo-Key`; the key is a `volo_sk_…` token stored only as a
   sha256 hash and returned exactly once at mint time, scoped to its workspace (cross-workspace →
   403). *Management* routes (create team/workspace/key) reuse the OSS `require_principal` seam —
   open in local dev, and denied to anonymous callers when `VOLO_REQUIRE_AUTH=true`. That flag is
   the documented swap point for a real user-auth vendor (Clerk/Supabase JWT) in `auth.py`, which
   is a paid-dependency decision deferred to deployment, not baked into the code.

## Consequences

- The control plane is fully exercisable with `uv run` and SQLite — a contributor can develop and
  test the commercial tier with no accounts and no spend, keeping faith with §11.
- API-key auth is real and sufficient for machine/CI access (the primary use); human SSO/RBAC is
  intentionally out of this MVP (that's M30) — management routes are a thin seam awaiting the
  vendor.
- Storing only the key hash means a leaked database can't recover keys; the tradeoff is keys are
  unrecoverable and must be re-minted, which is the correct posture.
- Because cloud tables share `SQLModel.metadata`, `init_schema` on any engine creates them too;
  harmless (unused tables) for OSS-only deployments, and the `cloud_*` prefix avoids collisions.

## Alternatives considered

- **A hosted GitHub-App-style service with a bundled auth vendor** — rejected for the MVP: forces
  a paid dependency and a specific vendor before there's a design partner; the pluggable seam +
  API keys deliver the workspace/history value now and let the vendor be chosen later.
- **Put cloud code under `services/`** — rejected: it must be a clearly separate licensing island,
  not mixed with the Apache-2.0 `services/api`; a top-level `cloud/` with its own LICENSE makes the
  boundary unmistakable (à la Sentry/Phoenix).
- **Encrypt keys instead of hashing** — rejected: hashing is simpler and strictly safer for an
  auth token (we never need the plaintext back); one-time display is the standard pattern.
