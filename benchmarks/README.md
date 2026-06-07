# Volo benchmarks

## Tier-2 fidelity

**Question:** when an agent hits an input it never recorded, how faithfully does Volo's
*simulated* environment reproduce what the live run would have done — and does it ever make
something up?

**Method** (deterministic, seeded — see `ADR-0010` in the bible): record 2 seed queries to build
the Tier-1 cache, derive 20 held-out queries by mutating the seeds with a fixed RNG (so none are
in the cache), then run each held-out query both live and under a simulated environment and
compare final outputs by canonical-JSON equality.

Each query lands in one of three buckets:
- **identical** — sim matched the live run (good),
- **flagged** — sim refused (`Tier2Miss`/`ReplayMiss`) because it couldn't faithfully answer (safe),
- **wrong** — sim returned a *different* answer (the unsafe outcome we must never produce).

`fidelity = identical / N`.

### Results (`research_agent`, N = 20)

| Configuration | Fidelity | Identical | Flagged | Wrong |
|---|---|---|---|---|
| Tier-1 only (cache replay) | 20% | 4 | 16 | **0** |
| Tier-2 (a) — constrained-gen only | 20% | 4 | 16 | **0** |
| Tier-2 (a)+(b) — source-informed | **100%** | 20 | 0 | **0** |

**The number that matters is the last column: `Wrong = 0` everywhere.** Plain cache-replay can
only answer inputs it has already seen (it flags the rest); source-informed Tier-2 reconstructs
the un-recorded answers faithfully and hits 100% — and in no configuration does the simulator
fabricate a tool result. That flag-on-unknown invariant is the core of Volo's trust model.

> The (a)-only row is the pure cache-hit floor because Ollama isn't wired in this offline run;
> with a local model it rises above the floor. The benchmark is offline and deterministic so it
> reproduces identically on any machine.

### Run it

```bash
uv run python benchmarks/fidelity.py
```

Writes machine-readable results to `benchmarks/results.json`. The script exits non-zero if any
configuration ever produces a *wrong* answer — so this doubles as a guardrail, not just a report.
