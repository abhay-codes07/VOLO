"""Observability seam: structured logging + request-timing middleware (bible §9.6).

OSS-friendly and dependency-free — stdlib ``logging`` only, no structlog/OTel required.
A deployment sets ``VOLO_LOG_LEVEL`` (critical|error|warning|info|debug; default ``info``)
to control verbosity. Every request is logged once on completion with a stable request id,
method, path, status, and duration, so logs are greppable and aggregator-friendly.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

_LEVELS = {"critical", "error", "warning", "info", "debug"}
_LOGGER_NAME = "volo.api"


def log_level() -> int:
    """Resolve ``VOLO_LOG_LEVEL`` to a ``logging`` level int (default INFO)."""
    name = os.environ.get("VOLO_LOG_LEVEL", "info").strip().lower()
    if name not in _LEVELS:
        name = "info"
    return int(getattr(logging, name.upper()))


class _KeyValueFormatter(logging.Formatter):
    """Compact ``key=value`` lines — readable in a terminal, parseable by log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"ts={self.formatTime(record, '%Y-%m-%dT%H:%M:%S')}",
            f"level={record.levelname.lower()}",
            f"logger={record.name}",
            f"msg={record.getMessage()!r}",
        ]
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            parts.extend(f"{k}={v!r}" for k, v in fields.items())
        return " ".join(parts)


_configured = False


def configure_logging() -> logging.Logger:
    """Install the key=value handler at ``VOLO_LOG_LEVEL`` and align uvicorn's loggers.

    Idempotent: safe to call once per ``create_app`` even when several apps are built in the
    same process (tests). Returns the ``volo.api`` logger.
    """
    global _configured
    level = log_level()
    handler = logging.StreamHandler()
    handler.setFormatter(_KeyValueFormatter())

    if not _configured:
        logging.basicConfig(level=level, handlers=[handler], force=True)
        # Route uvicorn's own loggers through the same handler instead of its default format.
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            uv_logger = logging.getLogger(name)
            uv_logger.handlers = [handler]
            uv_logger.propagate = False
            uv_logger.setLevel(level)
        _configured = True

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    return logger


def install_request_logging(app: FastAPI, logger: logging.Logger) -> None:
    """Add an HTTP middleware that logs one line per request with timing + a request id.

    The id is taken from an inbound ``X-Request-ID`` header when present (trace propagation)
    or generated, and is echoed back on the response so clients/proxies can correlate.
    """

    @app.middleware("http")
    async def _log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            dur_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request failed",
                extra={
                    "fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "dur_ms": dur_ms,
                    }
                },
            )
            raise
        dur_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "dur_ms": dur_ms,
                }
            },
        )
        return response


__all__ = ["configure_logging", "install_request_logging", "log_level"]
