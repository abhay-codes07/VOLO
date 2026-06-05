"""Smoke tests for the deterministic-by-construction ports."""

from __future__ import annotations

from volo_core.interfaces import FrozenClock, SeededRandom


def test_frozen_clock_advances_deterministically() -> None:
    c = FrozenClock("2026-01-01T00:00:00+00:00", step_seconds=1.0)
    t1 = c.now_iso()
    t2 = c.now_iso()
    assert t1 < t2
    assert t1.startswith("2026-01-01T00:00:00")
    assert t2.startswith("2026-01-01T00:00:01")


def test_seeded_random_is_reproducible() -> None:
    a = SeededRandom(seed=42)
    b = SeededRandom(seed=42)
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]
