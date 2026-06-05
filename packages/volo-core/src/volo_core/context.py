"""Active-recorder ``ContextVar`` machinery — see ADR-0004.

The Recorder uses ``set_active_recorder`` on enter / restore on exit; proxies call
``get_active_recorder`` per intercepted call. ``ContextVar`` is async-safe and survives
``asyncio.create_task`` boundaries, so async agents work correctly.

This module is in ``volo-core`` because both the SDK (sets) and the simulator (reads, for
replay-time proxies) need access; per the hexagonal rule, neither package may depend on the other.

The concrete recorder type is intentionally typed as ``Any`` here so ``volo-core`` does not
depend on ``volo-sdk``; the SDK defines a ``ActiveRecorder`` ``Protocol`` for proxies to use.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_active: ContextVar[Any | None] = ContextVar("agentsim_active_recorder", default=None)
_env: ContextVar[Any | None] = ContextVar("agentsim_active_environment", default=None)


def set_active_recorder(recorder: Any) -> Token[Any | None]:
    """Install ``recorder`` as the active one and return a restoration token."""
    return _active.set(recorder)


def reset_active_recorder(token: Token[Any | None]) -> None:
    _active.reset(token)


def get_active_recorder() -> Any | None:
    return _active.get()


@contextmanager
def current_recorder(recorder: Any) -> Iterator[Any]:
    """Scope ``recorder`` as active for the duration of the ``with`` block."""
    token = set_active_recorder(recorder)
    try:
        yield recorder
    finally:
        reset_active_recorder(token)


def set_active_environment(env: Any) -> Token[Any | None]:
    """Install a ``SimulatedEnvironment`` to take over model+tool calls from proxies."""
    return _env.set(env)


def reset_active_environment(token: Token[Any | None]) -> None:
    _env.reset(token)


def get_active_environment() -> Any | None:
    return _env.get()


@contextmanager
def current_environment(env: Any) -> Iterator[Any]:
    """Scope ``env`` as active for the duration of the ``with`` block.

    When set, capture proxies delegate to ``env.model_provider()`` and ``env.tool_registry()``
    instead of their constructed-time inner provider. This is how replay mode swaps in.
    """
    token = set_active_environment(env)
    try:
        yield env
    finally:
        reset_active_environment(token)
