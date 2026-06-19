# ADR 0013: Deployment images + API observability seam

- **Status:** accepted
- **Date:** 2026-06-20
- **Deciders:** founder
- **Related:** bible §9.6 (API service), §13 (deferred launch items), ADR-0012 (security
  trust boundaries — opt-in auth)

## Context

M9 (launch hardening) deferred "deployment + observability" to the end. Two concrete gaps
blocked a real deploy:

1. **`docker-compose.yml` referenced Dockerfiles that did not exist** (`services/api/Dockerfile`,
   `apps/web/Dockerfile`). The documented one-command stack could not build.
2. **The API configured no logging at all.** `VOLO_LOG_LEVEL` was named in the compose file but
   never consumed, and there was no request-level visibility — unworkable for any deployment.

A third, smaller issue: `/healthz` carried `Depends(get_principal)`, so an orchestrator liveness
probe would 401 once `VOLO_REQUIRE_AUTH=true` (the posture ADR-0012 mandates off-localhost).

## Decision

### Container images
- **API image** (`services/api/Dockerfile`): `python:3.12-slim` + the `uv` binary; build context
  is the **repo root** (the api depends on the in-tree `volo-*` workspace packages). Install is
  `uv sync --frozen --no-dev --package volo-api --extra serve`, pinned to `uv.lock`. Runs
  unprivileged (`uid 10001`), serves `uvicorn volo_api.main:create_app --factory` on `:8080`,
  with a `HEALTHCHECK` against `/healthz`.
- **Web image** (`apps/web/Dockerfile`): multi-stage Node 20. Relies on Next's
  `output: "standalone"` (added to `next.config.ts`) so the runtime stage ships only the traced
  server bundle + static assets, unprivileged.
- A root **`.dockerignore`** keeps `.venv`, `node_modules`, `.git`, local `.volo` data, and
  `.env` out of the build context (smaller images, no secrets baked in).

### Observability seam (`volo_api/observability.py`)
- **Stdlib logging only — no new deps** (no structlog/OTel). A compact `key=value` formatter is
  installed at `VOLO_LOG_LEVEL` (default `info`); uvicorn's own loggers are routed through it.
- A **request-logging middleware** emits one line per request with a stable **request id**
  (inbound `X-Request-ID` honored for trace propagation, else generated; echoed on the response),
  method, path, status, and duration. Added innermost so CORS stays outermost.
- **`/healthz` is now unauthenticated** — liveness/readiness probes must work under
  `VOLO_REQUIRE_AUTH`; it returns no sensitive data.

### Web toolchain fixes surfaced by the first real container build / test run
The web image was the first time `npm install` + `next build` + `vitest` actually ran clean
(CI uses pnpm and only `typecheck`s, so these never executed before):
- **`apps/web/.npmrc` → `legacy-peer-deps=true`**: `@visx/*` still declares a React ≤18 peer
  range but works on React 19; this lets `npm install` resolve instead of `ERESOLVE`-ing.
- **`@testing-library/dom` added explicitly**: it's a peer of `@testing-library/react@16`;
  `legacy-peer-deps` disables peer auto-install, so `screen` would otherwise be unresolved.
- **`JSX.IntrinsicElements` → imported `JSX` from `react`**: React 19's `@types/react` dropped
  the global `JSX` namespace.
- **`vitest.config.ts` now registers `@vitejs/plugin-react`**: it was installed but never wired,
  so JSX compiled without the automatic runtime ("React is not defined").

## Consequences

- `docker compose up` builds and serves both services; both images were verified to build and
  answer HTTP (`/healthz` 200 with structured logs + `X-Request-ID`; web returns 200).
- Logs are greppable and aggregator-friendly with zero added dependencies; a deployment tunes
  verbosity via `VOLO_LOG_LEVEL` and correlates via `X-Request-ID`.
- The web app builds for production (standalone) and its unit tests run green.
- **Not done here:** the demo gif (`docs/demo.tape`, [VHS](https://github.com/charmbracelet/vhs),
  shipped session 07) is reproducible but not yet rendered (vhs not installed). CI does not yet
  build the Docker images or run the web `build`/`vitest` — a follow-up.
