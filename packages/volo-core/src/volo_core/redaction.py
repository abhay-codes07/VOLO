"""Redaction primitives. Run before persisting a Recording (bible §7.5)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from volo_core.recording import Recording

REDACTED = "[REDACTED]"

# Default high-precision patterns. Conservative on purpose — false negatives are worse than
# false positives when a key escapes to disk.
_DEFAULT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("openai_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9\-_]{20,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}")),
    ("stripe_key", re.compile(r"[sr]k_(?:live|test)_[0-9A-Za-z]{16,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("bearer_header", re.compile(r"(?i)Bearer\s+[A-Za-z0-9\.\-_]{16,}")),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
)

_DEFAULT_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "secret",
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "client_secret",
        "private_key",
        "x-api-key",
    }
)


@dataclass(frozen=True)
class RedactionConfig:
    """Configure the redaction pass.

    Defaults catch common API-key shapes and PII (email). Extend ``extra_patterns`` for
    project-specific secrets; extend ``secret_keys`` for additional sensitive field names.
    """

    patterns: tuple[tuple[str, re.Pattern[str]], ...] = _DEFAULT_PATTERNS
    extra_patterns: tuple[tuple[str, re.Pattern[str]], ...] = field(default_factory=tuple)
    secret_keys: frozenset[str] = _DEFAULT_SECRET_KEYS
    replacement: str = REDACTED

    def all_patterns(self) -> Iterable[tuple[str, re.Pattern[str]]]:
        yield from self.patterns
        yield from self.extra_patterns


def redact_value(value: Any, config: RedactionConfig | None = None) -> Any:
    """Recursively redact secrets in arbitrary nested data.

    Returns a deep copy; the input is never mutated. Behavior:

    * Strings → all configured regex patterns are replaced with ``config.replacement``.
    * Dicts → keys matching ``config.secret_keys`` (case-insensitive) have their entire value
      replaced; remaining values are recursed into.
    * Lists / tuples → each element is recursed.
    * Other types → returned unchanged.
    """
    cfg = config or RedactionConfig()
    return _redact(deepcopy(value), cfg)


def _redact(value: Any, cfg: RedactionConfig) -> Any:
    if isinstance(value, str):
        out = value
        for _, pattern in cfg.all_patterns():
            out = pattern.sub(cfg.replacement, out)
        return out
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in cfg.secret_keys:
                result[k] = cfg.replacement
            else:
                result[k] = _redact(v, cfg)
        return result
    if isinstance(value, list):
        return [_redact(v, cfg) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact(v, cfg) for v in value)
    return value


def redact_recording(recording: Recording, config: RedactionConfig | None = None) -> Recording:
    """Return a new ``Recording`` with secrets / PII stripped from inputs and outputs.

    Sets ``redaction_applied = True`` on the returned copy so downstream consumers know not to
    redact again.
    """
    cfg = config or RedactionConfig()
    raw = recording.model_dump(mode="python", by_alias=True)
    cleaned = _redact(raw, cfg)
    cleaned["redaction_applied"] = True
    return Recording.model_validate(cleaned)
