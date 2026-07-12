# Deploying Volo

Volo is open-core. There are three deployable surfaces; deploy only what you need.

| Surface | What it is | License |
|---|---|---|
| **CLI** (`volo`) | record / sim / run / ci / diff / certify … — the whole OSS testing engine | Apache-2.0 |
| **Dashboard** | `services/api` (FastAPI) + `apps/web` (Next.js) — local run history + trajectories | Apache-2.0 |
| **Cloud control plane** | `cloud/` — teams / RBAC / SSO / API keys / hosted sim-minutes | Commercial (`cloud/LICENSE`) |

Everything runs locally on SQLite with zero accounts; the pieces below are only for a hosted install.

---

## 0. Prerequisites

- Python ≥ 3.12 via [uv](https://docs.astral.sh/uv/) ≥ 0.5
- Node ≥ 20 (only for the web dashboard)
- `make setup` installs both toolchains and syncs dependencies.

Verify a green tree before shipping:

```bash
make test      # full pytest + vitest
make lint      # ruff + mypy + eslint + tsc
```

## 1. CLI (the OSS product)

The CLI is the primary artifact — publish it to PyPI or run from source.

```bash
uv run volo --help                      # from source
uv build --package volo-cli             # -> dist/*.whl for `pip install`
```

Consumers install `volo-cli` (which pulls the workspace packages) and run `volo ci` in their own
CI to gate agent reliability at ~$0. No server required.

## 2. Dashboard (optional, self-host)

```bash
# API (FastAPI) — reads the same VOLO_DB_URL as the CLI
uv run --package volo-api uvicorn volo_api.main:app --host 0.0.0.0 --port 8080
# Web (Next.js)
cd apps/web && npm ci && npm run build && npm start
```

Config: `VOLO_DB_URL` (SQLite default, or a Postgres DSN), `VOLO_REQUIRE_AUTH=true` to gate writes.
Point the web app at the API's URL.

## 3. Cloud control plane (commercial)

Deploy artifacts live in [`cloud/deploy/`](../cloud/deploy/) — two images (API + sim-minutes
worker) and a Fly.io manifest. See [`cloud/deploy/README.md`](../cloud/deploy/README.md) for the
full walkthrough. In brief:

```bash
docker build -f cloud/deploy/Dockerfile.api    -t volo-cloud-api    .   # uvicorn factory :8080
docker build -f cloud/deploy/Dockerfile.worker -t volo-cloud-worker .   # volo-cloud-worker loop
```

Required config (env / secrets):

| Variable | For | Notes |
|---|---|---|
| `VOLO_DB_URL` | API + worker | **Postgres** DSN in production (shared by both) |
| `VOLO_REQUIRE_AUTH=true` | API | deny anonymous callers |
| `VOLO_JWT_JWKS` **or** `VOLO_JWT_SECRET` | API | SSO — an IdP's JWKS (RS256) or a shared secret (HS256); `VOLO_JWT_ISS`/`VOLO_JWT_AUD` optional |
| `VOLO_SIM_AGENT_ALLOWLIST` | worker | comma-separated agents the worker may execute (safe-by-default) |

**Security:** the sim-minutes worker executes a job's agent code only if it is allowlisted; in
production also sandbox the worker container per job (treat it as an untrusted-code boundary).

## 4. Signing keys (packs / evidence / certificates)

Signing is HMAC (shared secret) by default; Ed25519 (asymmetric) is available where a public
credential must be verified without holding a forgeable secret:

```python
from volo_core import generate_keypair          # (private_pem, public_pem)
from volo_certify import sign_certificate_ed25519, verify_certificate
```

Keep private keys in your secret store; distribute only public keys in verifier keyrings. Never
commit secrets — `.env` is git-ignored.

## 5. Release checklist

1. `make test && make lint` green on `main`.
2. Bump versions if publishing packages; tag `vX.Y.Z`.
3. Publish the CLI wheel (PyPI) and/or deploy the dashboard / cloud images.
4. Set the production secrets above — never bake them into an image.
