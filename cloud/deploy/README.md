# Deploying Volo Cloud (hosted sim-minutes)

The commercial control plane (M26/M30) + the sim-minutes worker (M27) run locally on SQLite with
zero infra. This directory packages them for a hosted deployment: two container images (API +
worker) and a Fly.io manifest. **Nothing here changes application behavior** — it's packaging.

## Images

Both build from the **repo root** (the cloud app is a uv-workspace member):

```bash
docker build -f cloud/deploy/Dockerfile.api    -t volo-cloud-api    .
docker build -f cloud/deploy/Dockerfile.worker -t volo-cloud-worker .
```

- **API** — `uvicorn volo_cloud.app:create_cloud_app --factory` on port 8080.
- **Worker** — `volo-cloud-worker --poll 2`, the queue drain loop.

## Configuration (env / secrets)

| Variable | Purpose |
|---|---|
| `VOLO_DB_URL` | **Postgres** DSN shared by API + worker (e.g. `postgresql://…`). Defaults to local SQLite if unset. |
| `VOLO_REQUIRE_AUTH` | `true` in a hosted deployment — denies anonymous callers (set in the image/manifest). |
| `VOLO_JWT_JWKS` *or* `VOLO_JWT_SECRET` | SSO: an IdP's JWKS (RS256) or a shared secret (HS256). `VOLO_JWT_ISS` / `VOLO_JWT_AUD` optional. |
| `VOLO_SIM_AGENT_ALLOWLIST` | Comma-separated agents the **worker** may execute (safe-by-default, ADR-0033). |

> **Security:** the worker executes a job's agent code only if it's allowlisted. In production also
> sandbox the worker container per job — treat it as an untrusted-code boundary.

## Fly.io

`fly.toml` runs one image with two processes (`app`, `worker`). A first deploy:

```bash
fly launch --copy-config --no-deploy          # uses cloud/deploy/fly.toml
fly postgres create && fly postgres attach …  # sets VOLO_DB_URL (DATABASE_URL) as a secret
fly secrets set VOLO_JWT_JWKS='{"keys":[…]}' VOLO_SIM_AGENT_ALLOWLIST='my_pkg.agent:run'
fly deploy
```

Scale the worker independently of the API:

```bash
fly scale count app=1 worker=2
```

The same images run on any container host (Cloud Run, ECS, a plain VM) — set the same env and run
the two commands. A slimmer cloud-only image (syncing just `volo-cloud` instead of the whole
workspace) is a reasonable follow-up optimization.
