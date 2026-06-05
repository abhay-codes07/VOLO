# `services/api`

FastAPI backend for the Volo dashboard and (eventually) the cloud service.

> **Status:** placeholder. The first real route lands when the dashboard needs to read
> Recordings. Tracked in [`docs/ROADMAP.md`](../../docs/ROADMAP.md) M6.

When it exists, the local dev command will be:

```bash
make dev-api
# uv run --package volo-api uvicorn volo_api.main:app --reload --port 8080
```
