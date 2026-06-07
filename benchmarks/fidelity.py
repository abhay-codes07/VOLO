"""Tier-2 fidelity benchmark - how faithfully does the *simulated* environment reproduce a
live agent run on inputs it never recorded?

Methodology (deterministic, seeded; see ADR-0010):
- Seed set: 2 recorded queries build the Tier-1 cache.
- Held-out set: N queries derived by mutating the seeds with a seeded RNG (never recorded).
- For each held-out query we run the agent (a) live and (b) under a simulated environment, then
  compare final outputs by canonical-JSON equality.
- Outcomes per query: ``identical`` (sim == live), ``flagged`` (sim refused → Tier2Miss, the
  safe outcome), or ``wrong`` (sim produced a *different* answer - the unsafe outcome we must
  never see). Fidelity = identical / N.

Run:  uv run python benchmarks/fidelity.py
"""

from __future__ import annotations

import json
import random
import sys
from collections.abc import Callable
from pathlib import Path

# Make the repo root importable (examples/, volo_*), regardless of CWD.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.research_agent import run, tool_specs  # noqa: E402

from volo_core import Recording, canonical_json, current_environment, current_recorder  # noqa: E402
from volo_sdk import Recorder, RecorderConfig  # noqa: E402
from volo_simulator import (  # noqa: E402
    OllamaConstrainedSynthesizer,
    ReplayMiss,
    SourceInformedSynthesizer,
    Tier1Replayer,
    Tier2Miss,
    Tier2Replayer,
)

SEED_QUERIES = ["volo", "claude code"]
N_HELD_OUT = 20
RNG_SEED = 0xC0FFEE


def _baseline() -> Recording:
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    rec.recording.tool_specs = tool_specs()
    with current_recorder(rec):
        for q in SEED_QUERIES:
            rec.set_final_output(run({"query": q}))
    return rec.recording


def _mutate(seed: str, rng: random.Random) -> str:
    moves: list[Callable[[str], str]] = [
        lambda s: s.upper(),
        lambda s: s + " " + rng.choice(["docs", "blog", "release", "tutorial"]),
        lambda s: " ".join(reversed(s.split())),
        lambda s: s.replace(" ", "_"),
        lambda s: s + "?" * rng.randint(1, 3),
        lambda s: s.title(),
    ]
    return rng.choice(moves)(seed)


def _held_out() -> list[str]:
    rng = random.Random(RNG_SEED)
    return [_mutate(rng.choice(SEED_QUERIES), rng) for _ in range(N_HELD_OUT)]


class _EmptyOllama:
    """Stands in for an unavailable Ollama - abstains, so (a)-only measures the cache floor."""

    def complete(self, request: dict[str, object]) -> dict[str, str]:
        return {"text": ""}


def _score(label: str, env_factory: Callable[[], object]) -> dict[str, object]:
    identical = flagged = wrong = 0
    for q in _held_out():
        live = canonical_json(run({"query": q}))
        env = env_factory()
        with current_environment(env):
            try:
                sim_raw: object = run({"query": q})
            except (Tier2Miss, ReplayMiss) as e:
                sim_raw = {"__flagged__": str(e)}
        if isinstance(sim_raw, dict) and "__flagged__" in sim_raw:
            flagged += 1
        elif canonical_json(sim_raw) == live:
            identical += 1
        else:
            wrong += 1
    return {
        "config": label,
        "n": N_HELD_OUT,
        "identical": identical,
        "flagged": flagged,
        "wrong": wrong,
        "fidelity": round(identical / N_HELD_OUT, 4),
    }


def main() -> None:
    baseline = _baseline()
    configs: list[tuple[str, Callable[[], object]]] = [
        ("Tier-1 only (cache replay)", lambda: Tier1Replayer.from_recording(baseline)),
        (
            "Tier-2 (a) - constrained-gen only",
            lambda: Tier2Replayer(
                baseline, synthesizers=[OllamaConstrainedSynthesizer(provider=_EmptyOllama())]
            ),
        ),
        (
            "Tier-2 (a)+(b) - source-informed",
            lambda: Tier2Replayer(
                baseline,
                synthesizers=[
                    SourceInformedSynthesizer(trust_source_hints=True),
                    OllamaConstrainedSynthesizer(provider=_EmptyOllama()),
                ],
            ),
        ),
    ]
    results = [_score(label, factory) for label, factory in configs]

    print(f"\nTier-2 fidelity benchmark - research_agent, N={N_HELD_OUT} held-out queries\n")
    print("| Configuration | Fidelity | Identical | Flagged | Wrong |")
    print("|---|---|---|---|---|")
    for r in results:
        print(
            f"| {r['config']} | {float(r['fidelity']):.0%} | "
            f"{r['identical']} | {r['flagged']} | {r['wrong']} |"
        )
    print(
        "\nNote: Ollama is not wired in this offline benchmark, so the (a)-only row is the "
        "pure cache-hit floor. The invariant that matters: **Wrong = 0 everywhere** - the "
        "simulator flags what it can't reproduce rather than fabricating.\n"
    )

    out = _ROOT / "benchmarks" / "results.json"
    out.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"results -> {out}")

    if any(r["wrong"] for r in results):
        raise SystemExit("FAIL: a configuration produced a wrong answer instead of flagging.")


if __name__ == "__main__":
    main()
