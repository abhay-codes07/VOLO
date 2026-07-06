"""Perf guard (M19): replay throughput stays well above the 10k steps/min floor.

Uses a generous floor so it never flakes on a slow CI box, while still catching an
order-of-magnitude regression in the Tier-1 replay path.
"""

from __future__ import annotations

from benchmarks.replay_throughput import measure

FLOOR_STEPS_PER_MIN = 10_000


def test_replay_throughput_above_floor() -> None:
    r = measure(5_000)
    assert r["total_steps_per_min"] > FLOOR_STEPS_PER_MIN, r
