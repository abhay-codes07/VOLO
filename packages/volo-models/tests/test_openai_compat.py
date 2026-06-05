"""Tests for the generic OpenAI-compatible provider (bible §11, Groq free-tier default).

No live network: the ``transport`` seam replays a recorded Groq response fixture, so the suite
is deterministic and cost-free in CI. The opt-in gate and key resolution are exercised
directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from volo_models import (
    CachedProvider,
    OpenAICompatProvider,
    OpenAICompatUnavailable,
)
from volo_models.openai_compat import OPT_IN_ENV, PRESETS

_FIXTURE = Path(__file__).parent / "fixtures" / "groq_chat_completion.json"


def _recorded_response() -> dict[str, Any]:
    return json.loads(_FIXTURE.read_text())


class _RecordingTransport:
    """A ``transport`` that captures the request and replays a fixed response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": json.loads(body),
                "timeout": timeout,
            }
        )
        return self.response


@pytest.fixture
def opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OPT_IN_ENV, "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")


# ── gating ────────────────────────────────────────────────────────────────────


def test_refuses_without_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(OPT_IN_ENV, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "k")
    prov = OpenAICompatProvider(transport=_RecordingTransport(_recorded_response()))
    with pytest.raises(OpenAICompatUnavailable, match="opt-in"):
        prov.complete({"prompt": "hi"})


def test_refuses_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OPT_IN_ENV, "true")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    prov = OpenAICompatProvider(transport=_RecordingTransport(_recorded_response()))
    with pytest.raises(OpenAICompatUnavailable, match="GROQ_API_KEY"):
        prov.complete({"prompt": "hi"})


# ── happy path (replayed fixture) ───────────────────────────────────────────────


def test_completes_from_recorded_response(opted_in: None) -> None:
    transport = _RecordingTransport(_recorded_response())
    prov = OpenAICompatProvider(transport=transport)
    out = prov.complete({"prompt": "score this", "format": "json"})

    assert out["text"] == '{"score": 0.92}'
    assert out["response"] == out["text"]
    assert out["stop_reason"] == "stop"
    assert out["_provider"] == "groq"
    assert out["_model"] == "llama-3.3-70b-versatile"
    assert out["_cost_usd"] == 0.0  # free tier, by design
    assert out["usage"]["total_tokens"] == 223


def test_builds_openai_payload_and_auth_header(opted_in: None) -> None:
    transport = _RecordingTransport(_recorded_response())
    prov = OpenAICompatProvider(transport=transport)
    prov.complete({"system": "be terse", "prompt": "hello", "format": "json"})

    call = transport.calls[0]
    assert call["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer test-key-123"
    payload = call["payload"]
    assert payload["model"] == "llama-3.3-70b-versatile"
    assert payload["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hello"},
    ]
    assert payload["temperature"] == 0.0
    assert payload["response_format"] == {"type": "json_object"}


def test_sends_browser_user_agent(opted_in: None) -> None:
    # Cloudflare (in front of Groq) blocks the default urllib agent with error 1010, so a
    # browser-style User-Agent is required for live calls to succeed.
    transport = _RecordingTransport(_recorded_response())
    OpenAICompatProvider(transport=transport).complete({"prompt": "x"})
    assert transport.calls[0]["headers"]["User-Agent"].startswith("Mozilla/")


def test_passes_through_explicit_messages(opted_in: None) -> None:
    transport = _RecordingTransport(_recorded_response())
    prov = OpenAICompatProvider(transport=transport)
    msgs = [{"role": "user", "content": "direct"}]
    prov.complete({"messages": msgs})
    assert transport.calls[0]["payload"]["messages"] == msgs


# ── backend selection ───────────────────────────────────────────────────────────


def test_preset_switches_base_url_and_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OPT_IN_ENV, "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    transport = _RecordingTransport(_recorded_response())
    prov = OpenAICompatProvider(preset="openrouter", transport=transport)
    prov.complete({"prompt": "x"})
    call = transport.calls[0]
    assert call["url"].startswith("https://openrouter.ai/api/v1")
    assert call["headers"]["Authorization"] == "Bearer or-key"


def test_unknown_preset_rejected() -> None:
    with pytest.raises(ValueError, match="unknown preset"):
        OpenAICompatProvider(preset="nope")


def test_all_presets_have_required_fields() -> None:
    for name, p in PRESETS.items():
        assert p.base_url.startswith("https://"), name
        assert p.model and p.key_env and p.provider, name


# ── error handling + caching (the "replayed in CI" story end-to-end) ────────────


def test_network_error_surfaces_as_unavailable(opted_in: None) -> None:
    # Default (real) transport against a closed port → wrapped as OpenAICompatUnavailable.
    prov = OpenAICompatProvider(base_url="http://127.0.0.1:1/v1", timeout=1.0)
    with pytest.raises(OpenAICompatUnavailable, match="could not reach"):
        prov.complete({"prompt": "hi"})


def test_cached_provider_replays_without_second_call(opted_in: None) -> None:
    transport = _RecordingTransport(_recorded_response())
    cached = CachedProvider(
        OpenAICompatProvider(transport=transport),
        provider="groq",
        model="llama-3.3-70b-versatile",
    )
    a = cached.complete({"prompt": "same"})
    b = cached.complete({"prompt": "same"})
    assert a == b
    assert len(transport.calls) == 1  # second call served from cache — zero network
