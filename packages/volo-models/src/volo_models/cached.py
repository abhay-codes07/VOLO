"""``CachedProvider`` — wrap any ``ModelProvider`` with a content-addressed in-memory cache."""

from __future__ import annotations

from typing import Any

from volo_core import cache_key
from volo_core.interfaces import ModelProvider


class CachedProvider(ModelProvider):
    def __init__(self, inner: ModelProvider, *, provider: str = "?", model: str = "?") -> None:
        self._inner = inner
        self._provider = provider
        self._model = model
        self._cache: dict[str, dict[str, Any]] = {}

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        key = cache_key(self._provider, self._model, request)
        hit = self._cache.get(key)
        if hit is not None:
            return dict(hit)
        response = self._inner.complete(request)
        self._cache[key] = dict(response)
        return response

    def stats(self) -> dict[str, int]:
        return {"entries": len(self._cache)}
