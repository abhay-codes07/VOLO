# Volo

> **Deterministic testing for AI agents — in CI, at ~$0.** Record your agent run once, replay it
> against a high-fidelity simulated environment that never hallucinates, and block reliability
> regressions in your pull requests. Like unit tests and `git bisect`, but for agents.

Most agent "evals" re-run a live LLM-as-judge on every check — which costs API money *and is
itself non-deterministic*. Volo flips that: it **replays a recorded run deterministically against
mocked tools**, so the same PR check gives the same answer every time, for free.

---

## Why

Teams ship AI agents that fail non-deterministically and can't be tested like normal software.
Going from "80% works in a pilot" to "99%+ in production" can take 100× the original build
effort. Today's tools either trace agents *after* they fail in production or run shallow
benchmarks that don't reflect reality.

Volo makes agents testable the way regular software is testable:

1. **Record** a real run once — every model call, tool call, and decision.
2. **Simulate** the agent's full environment — not just cache-replay, but a stateful,
   source-informed simulator that handles inputs you never recorded (and flags, never
   hallucinates, when it can't).
3. **Generate adversarial scenarios** automatically: dropped tool results, ambiguous turns,
   prompt injection, long-horizon drift.
4. **Measure reliability** across orthogonal dimensions: trajectory determinism, decision
   determinism, faithfulness, consistency-under-repetition.
5. **Block regressions in CI** — every PR runs the suite deterministically at $0 marginal cost.
6. **Root-cause and diff** — "git bisect for agents" pinpoints the breaking step and the commit.

## Quickstart (local)

> Requires: `uv ≥ 0.5`, Node ≥ 20 with `corepack` enabled.

```bash
git clone https://github.com/abhay-codes07/VOLO.git
cd VOLO
make setup        # installs Python (uv) + JS toolchains, syncs deps
make test         # full test suite
uv run volo --help
```

A minimal record → replay loop on a bundled example:

```bash
uv run volo record examples.echo_agent:run --out ./.volo/recordings/echo.json
uv run volo sim ./.volo/recordings/echo.json     # deterministic replay, $0
```

Score an agent against the adversarial scenario suite and get a ship / no-ship verdict:

```bash
uv run volo run ./.volo/recordings/echo.json --agent examples.echo_agent:run
```

### Optional: a free LLM judge

Faithfulness can be scored by a local heuristic (default, free, deterministic), local Ollama, or
a free OpenAI-compatible API (Groq by default). Drop a key in `.env` (copy `.env.example`):

```env
VOLO_OPENAI_COMPAT_OPT_IN=true
GROQ_API_KEY=gsk_...
```

```bash
uv run volo run <recording> --agent <module:fn> --judge groq
```

## Architecture

Seven subsystems behind a CLI and a Next.js dashboard:

```
Capture SDK → Environment Simulator → Scenario Generator → Reliability Engine
       ↓                                                            ↓
    CI Runner ───────── Root-Cause / Diff ─────────────── Cost-Routing Brain
```

## Repo layout

```
packages/       # 9 Python packages (uv workspace) — one per subsystem + core + CLI
services/api/   # FastAPI backend (local dashboard + cloud seam)
apps/web/       # Next.js dashboard
integrations/   # framework adapters: langgraph, openai_agents, crewai
examples/       # runnable demo agents (also the CI dogfood targets)
tests/          # cross-package integration, e2e, and fidelity benchmarks
```

## Tech stack

Python 3.12+ (uv workspace), FastAPI, SQLModel + SQLite, Ollama for local judging, and a free
OpenAI-compatible provider for optional LLM judging. Frontend is Next.js + TypeScript + Tailwind.
Everything runs fully locally with zero cloud accounts.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
