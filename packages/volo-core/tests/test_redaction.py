"""Tests for the redaction pass. Bible §7.5."""

from __future__ import annotations

import re

from volo_core import (
    ModelCallPayload,
    Recording,
    RedactionConfig,
    ToolCallPayload,
    redact_recording,
    redact_value,
)


def test_redacts_anthropic_key_in_string() -> None:
    raw = "key=sk-ant-AAAAbbbb1111ccccDDDDeeeeFFFFggggHHHHiiii"
    out = redact_value(raw)
    assert "sk-ant" not in out
    assert "[REDACTED]" in out


def test_redacts_secret_keyed_dict_value_wholesale() -> None:
    raw = {"Authorization": "Bearer notreallyatoken-but-could-be-1234567890"}
    out = redact_value(raw)
    assert out["Authorization"] == "[REDACTED]"


def test_redacts_secret_keys_case_insensitively() -> None:
    raw = {"API_KEY": "anything", "Api_Key": "anything", "api_key": "anything"}
    out = redact_value(raw)
    assert set(out.values()) == {"[REDACTED]"}


def test_recurses_into_nested_structures() -> None:
    raw = {
        "messages": [
            {"role": "user", "content": "my email is alice@example.com"},
            {"role": "assistant", "content": "noted"},
        ],
    }
    out = redact_value(raw)
    assert "alice@example.com" not in out["messages"][0]["content"]
    assert "[REDACTED]" in out["messages"][0]["content"]
    assert out["messages"][1]["content"] == "noted"


def test_redacts_additional_provider_key_shapes() -> None:
    """New default patterns (ADR-0012): Google / Slack / Stripe / JWT.

    Fixtures are assembled from fragments so these synthetic (non-real) values don't trip
    upstream secret scanners; the concatenated runtime strings still match the patterns.
    """
    samples = [
        "AIza" + "SyA1234567890abcdefghijklmnopqrstuvw",  # Google API key shape
        "xoxb-" + "1234567890-abcdefghijklmnopqrst",  # Slack bot token shape
        "sk_" + "live_" + "abcdEFGH1234ijklMNOP5678",  # Stripe live key shape
        "eyJhbGciOi." + "eyJzdWIiOiIxMjM0NTY." + "SflKxwRJSMeKKF2QT",  # JWT shape
    ]
    for s in samples:
        out = redact_value(f"value={s}")
        assert s not in out, f"leaked: {s}"
        assert "[REDACTED]" in out


def test_extra_patterns_extend_defaults() -> None:
    cfg = RedactionConfig(extra_patterns=(("internal_id", re.compile(r"EMP-\d{6}")),))
    assert "[REDACTED]" in redact_value("employee EMP-123456 leaked", cfg)


def test_redact_recording_marks_flag_and_strips_payloads() -> None:
    r = Recording()
    r.add_step(
        ModelCallPayload(
            provider="anthropic",
            model="haiku",
            request={"prompt": "key=sk-ant-AAAA1111BBBB2222CCCC3333DDDD4444EEEE"},
        ),
    )
    r.add_step(
        ToolCallPayload(
            tool="http_get",
            request={"headers": {"Authorization": "Bearer dummy-token-1234567890abcdef"}},
        ),
    )

    cleaned = redact_recording(r)

    assert cleaned.redaction_applied is True
    assert "sk-ant" not in cleaned.to_json()
    auth = cleaned.steps[1].payload.request["headers"]["Authorization"]  # type: ignore[union-attr]
    assert auth == "[REDACTED]"


def test_redact_does_not_mutate_input() -> None:
    raw = {"api_key": "secret"}
    _ = redact_value(raw)
    assert raw["api_key"] == "secret"
