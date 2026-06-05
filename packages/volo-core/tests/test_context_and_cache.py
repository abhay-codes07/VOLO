"""Tests for the active-recorder ContextVar and canonical request normalization."""

from __future__ import annotations

import asyncio

from volo_core import (
    cache_key,
    canonical_json,
    current_recorder,
    get_active_recorder,
)


def test_active_recorder_is_none_by_default() -> None:
    assert get_active_recorder() is None


def test_current_recorder_scope_sets_and_restores() -> None:
    marker = object()
    with current_recorder(marker):
        assert get_active_recorder() is marker
    assert get_active_recorder() is None


def test_nested_current_recorder_restores_outer() -> None:
    outer, inner = object(), object()
    with current_recorder(outer):
        assert get_active_recorder() is outer
        with current_recorder(inner):
            assert get_active_recorder() is inner
        assert get_active_recorder() is outer
    assert get_active_recorder() is None


def test_contextvar_is_async_safe() -> None:
    async def task(label: str, results: dict[str, object]) -> None:
        with current_recorder(label):
            await asyncio.sleep(0)
            results[label] = get_active_recorder()

    async def main() -> dict[str, object]:
        results: dict[str, object] = {}
        await asyncio.gather(task("a", results), task("b", results))
        return results

    out = asyncio.run(main())
    assert out == {"a": "a", "b": "b"}


def test_canonical_json_sorts_keys_and_normalizes_int_floats() -> None:
    assert canonical_json({"b": 1, "a": 2.0}) == '{"a":2,"b":1}'


def test_cache_key_is_stable_under_dict_order() -> None:
    a = cache_key("model_call", {"prompt": "hi", "n": 1})
    b = cache_key("model_call", {"n": 1, "prompt": "hi"})
    assert a == b


def test_cache_key_changes_with_content() -> None:
    a = cache_key("tool_call", "search", {"q": "x"})
    b = cache_key("tool_call", "search", {"q": "y"})
    assert a != b
