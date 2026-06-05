"""``OllamaProvider`` — local small-model backend (bible §5, §11).

Thin sync HTTP wrapper around the Ollama ``/api/generate`` endpoint. We intentionally use the
stdlib ``urllib`` so this package has zero runtime dependencies beyond ``volo-core`` — the
SDK's proxies do the capture/replay heavy lifting, so this provider is only ever invoked at
record time.

If Ollama is not running locally, ``complete()`` raises ``OllamaUnavailable``. The caller (the
SDK or a framework adapter) is responsible for surfacing this gracefully.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from volo_core.interfaces import ModelProvider


class OllamaUnavailable(RuntimeError):
    """Raised when the Ollama daemon is unreachable."""


class OllamaProvider(ModelProvider):
    def __init__(
        self,
        *,
        model: str = "llama3.2:3b",
        host: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        prompt = request.get("prompt")
        if prompt is None:
            messages = request.get("messages", [])
            prompt = "\n".join(m.get("content", "") for m in messages if isinstance(m, dict))
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise OllamaUnavailable(f"could not reach {self.host}: {e}") from e
        return {
            "text": raw.get("response", ""),
            "stop_reason": "end_turn" if raw.get("done") else "incomplete",
            "_provider": "ollama",
            "_model": self.model,
        }
