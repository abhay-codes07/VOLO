"""Replay throughput benchmark (M19 / ADR-0023 perf pass).

Builds a large synthetic recording, then times (a) the Tier-1 cache build and (b) serving every
recorded tool call back through the replayer. Prints steps/minute for each. Target: >= 10k
steps/min end-to-end (comfortably met — this exists to catch regressions, not to strain).

Run: ``uv run python benchmarks/replay_throughput.py [n_steps]``
"""

from __future__ import annotations

import sys
import time

from volo_core import Recording, ToolCallPayload
from volo_simulator import Tier1Replayer


def build_recording(n_steps: int) -> Recording:
    rec = Recording()
    for i in range(n_steps):
        rec.add_step(
            ToolCallPayload(tool="search", request={"i": i}, response={"hits": i, "ok": True})
        )
    return rec


def measure(n_steps: int) -> dict[str, float]:
    rec = build_recording(n_steps)

    t0 = time.perf_counter()
    env = Tier1Replayer.from_recording(rec)
    build_s = time.perf_counter() - t0

    reg = env.tool_registry()
    t1 = time.perf_counter()
    for i in range(n_steps):
        reg.call("search", {"i": i})
    serve_s = time.perf_counter() - t1

    total_s = build_s + serve_s
    return {
        "n_steps": n_steps,
        "build_s": build_s,
        "serve_s": serve_s,
        "build_steps_per_min": n_steps / build_s * 60 if build_s else float("inf"),
        "serve_steps_per_min": n_steps / serve_s * 60 if serve_s else float("inf"),
        "total_steps_per_min": n_steps / total_s * 60 if total_s else float("inf"),
    }


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
    r = measure(n)
    print(f"replay throughput over {r['n_steps']:,} steps:")
    print(
        f"  cache build : {r['build_s'] * 1000:8.1f} ms  ({r['build_steps_per_min']:,.0f} steps/min)"
    )
    print(
        f"  serve       : {r['serve_s'] * 1000:8.1f} ms  ({r['serve_steps_per_min']:,.0f} steps/min)"
    )
    print(f"  end-to-end  : {r['total_steps_per_min']:,.0f} steps/min")


if __name__ == "__main__":
    main()
