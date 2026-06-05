"""``OpenAICompatProvider`` — generic client for any OpenAI-compatible chat API (bible §11).

One client, many backends. Groq, Google Gemini, OpenRouter and xAI all expose the same
``POST {base_url}/chat/completions`` surface, so a single thin wrapper targets whichever the
founder configures — no code change to switch. Defaults to **Groq**, whose free tier makes it
the natural backend for the optional LLM judge.

Like ``OllamaProvider`` this is deliberately a stdlib ``urllib`` wrapper: the package keeps its
zero-runtime-dep promise, and live HTTP only ever happens at record time. In CI the SDK's
proxies (or the ``transport`` seam below) replay recorded responses, so tests cost nothing.

Gating (per founder decision, 2026-06-02): even though the configured backends are free, a
live network call still requires an explicit opt-in — ``VOLO_OPENAI_COMPAT_OPT_IN=true`` — so
CI can never make a surprise call. Cost is modelled as ``$0.00``; there is no ``Budget``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from volo_core.interfaces import ModelProvider

#: A ``transport`` is the testing seam: it takes the request envelope and returns the parsed
#: JSON response body, exactly as the HTTP backend would. The default hits the network.
Transport = Callable[[str, dict[str, str], bytes, float], dict[str, Any]]


class OpenAICompatUnavailable(RuntimeError):
    """Raised when the provider is not opted-in, has no API key, or the backend is unreachable."""


@dataclass(frozen=True)
class _Preset:
    base_url: str
    model: str
    key_env: str
    provider: str


#: Known free (or free-tier) OpenAI-compatible backends. ``xai`` is included for completeness
#: but its API is paid — selecting it is a deliberate cost choice, not a free one.
PRESETS: dict[str, _Preset] = {
    "groq": _Preset(
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        key_env="GROQ_API_KEY",
        provider="groq",
    ),
    "gemini": _Preset(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-2.0-flash",
        key_env="GEMINI_API_KEY",
        provider="gemini",
    ),
    "openrouter": _Preset(
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.3-70b-instruct:free",
        key_env="OPENROUTER_API_KEY",
        provider="openrouter",
    ),
    "xai": _Preset(
        base_url="https://api.x.ai/v1",
        model="grok-2-latest",
        key_env="XAI_API_KEY",
        provider="xai",
    ),
}

OPT_IN_ENV = "VOLO_OPENAI_COMPAT_OPT_IN"

# Some backends (Groq) sit behind Cloudflare, which blocks the default ``Python-urllib`` agent
# with "error code: 1010". A browser-style User-Agent is required for the request to be served.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _http_transport(
    url: str, headers: dict[str, str], body: bytes, timeout: float
) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            parsed: dict[str, Any] = json.loads(resp.read())
            return parsed
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise OpenAICompatUnavailable(f"could not reach {url}: {e}") from e


class OpenAICompatProvider(ModelProvider):
    """OpenAI-compatible chat-completions client. Defaults to Groq's free tier.

    Pick a backend with ``preset=`` (``"groq" | "gemini" | "openrouter" | "xai"``) or override
    any of ``base_url`` / ``model`` / ``key_env`` directly. The API key is read from the
    preset's env var unless passed explicitly.
    """

    def __init__(
        self,
        *,
        preset: str = "groq",
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        key_env: str | None = None,
        timeout: float = 30.0,
        user_agent: str = _DEFAULT_USER_AGENT,
        transport: Transport | None = None,
    ) -> None:
        if preset not in PRESETS:
            raise ValueError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
        p = PRESETS[preset]
        self.base_url = (base_url or p.base_url).rstrip("/")
        self.model = model or p.model
        self.provider = p.provider
        self._key_env = key_env or p.key_env
        self._api_key = api_key
        self.timeout = timeout
        self.user_agent = user_agent
        self._transport = transport or _http_transport

    def _resolve_key(self) -> str:
        key = self._api_key or os.environ.get(self._key_env)
        if not key:
            raise OpenAICompatUnavailable(
                f"no API key for provider={self.provider!r}; set ${self._key_env} "
                f"or pass api_key=.",
            )
        return key

    @staticmethod
    def _messages(request: dict[str, Any]) -> list[dict[str, str]]:
        messages = request.get("messages")
        if isinstance(messages, list) and messages:
            return messages
        msgs: list[dict[str, str]] = []
        system = request.get("system")
        if system:
            msgs.append({"role": "system", "content": str(system)})
        msgs.append({"role": "user", "content": str(request.get("prompt", ""))})
        return msgs

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        if os.environ.get(OPT_IN_ENV, "false").lower() != "true":
            raise OpenAICompatUnavailable(
                f"OpenAI-compatible calls are opt-in. Set {OPT_IN_ENV}=true to enable.",
            )
        key = self._resolve_key()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._messages(request),
            "temperature": float(request.get("temperature", 0.0)),
            "max_tokens": int(request.get("max_output_tokens", 512)),
        }
        # Honour JSON-mode requests (judge prompts ask for a strict JSON object).
        if request.get("format") == "json" or request.get("response_format"):
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": self.user_agent,
        }
        raw = self._transport(f"{self.base_url}/chat/completions", headers, body, self.timeout)

        choices = raw.get("choices") or []
        content = ""
        finish = "stop"
        if choices and isinstance(choices[0], dict):
            content = (choices[0].get("message") or {}).get("content", "") or ""
            finish = choices[0].get("finish_reason", "stop")
        return {
            "text": content,
            "response": content,
            "stop_reason": finish,
            "_provider": self.provider,
            "_model": raw.get("model", self.model),
            "_cost_usd": 0.0,  # free tier — no spend by design
            "usage": raw.get("usage"),
        }
