# Volo API — FastAPI service over local recordings + reliability reports.
# Build context is the repo root (see docker-compose.yml): the whole uv workspace
# is needed because volo-api depends on the in-tree volo-* packages.
#
#   docker build -f services/api/Dockerfile -t volo-api .
#   docker run -p 8080:8080 -v "$PWD/.volo:/data" volo-api

FROM python:3.12-slim AS base

# uv for fast, lockfile-pinned installs (matches the dev workflow).
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VOLO_DATA_DIR=/data \
    VOLO_LOG_LEVEL=info

WORKDIR /app

# Copy the workspace and install the api package (+ uvicorn via the `serve` extra),
# pinned to uv.lock. `--no-dev` drops pytest/ruff/mypy from the runtime image.
COPY . .
RUN uv sync --frozen --no-dev --package volo-api --extra serve

# Drop privileges and own the mounted data dir.
RUN useradd --create-home --uid 10001 volo \
    && mkdir -p /data \
    && chown -R volo:volo /data /app
USER volo

EXPOSE 8080

# /healthz is unauthenticated (liveness/readiness probes).
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["uv", "run", "--no-sync", "python", "-c", \
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/healthz').status==200 else 1)"]

CMD ["uv", "run", "--no-sync", "uvicorn", "volo_api.main:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080"]
