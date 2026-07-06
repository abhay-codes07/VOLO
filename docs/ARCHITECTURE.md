# Volo — Architecture

> Expansion of `VOLO_BUILD_BIBLE.md` §4. Read the bible section first; this doc adds
> implementation-level detail. ADRs in `docs/adr/` record decisions; this doc records the
> resulting **shape**.

## 1. The seven subsystems (bible §4.1)

```
 ┌──────────────────────────────────────────────────────┐
user's │ (1) CAPTURE SDK / PROXY                              │
agent ─►│ instruments any framework; records every model      │
        │ call, tool call, decision (OTel spans)              │
        └──────────────┬───────────────────────────────────────┘
                       ▼ Recording (trajectory + artifacts)
        ┌──────────────────────────────────────────────────────┐
        │ (2) ENVIRONMENT SIMULATOR   ← the moat               │
        │   Tier 1: deterministic cache-replay                 │
        │   Tier 2: source-/trace-informed stateful sim        │
        └──────┬───────────────────────────────────┬───────────┘
               ▼                                   ▼
   ┌────────────────────┐               ┌───────────────────────────┐
   │ (3) SCENARIO GEN   │               │ (4) RELIABILITY ENGINE    │
   │ adversarial muts:  │               │ trajectory + decision det │
   │ drop / corrupt /   │               │ faithfulness + consistency│
   │ inject_latency /   │               │ → reliability surface     │
   │ prompt_injection / │               └─────────────┬─────────────┘
   │ long_horizon …     │                             │
   └────────┬───────────┘                             │
            └──────────────────┬──────────────────────┘
                               ▼
        ┌──────────────────────────────────────────────────────┐
        │ (5) DETERMINISTIC CI RUNNER (CLI + GitHub Action)    │
        │ no live LLM/tool calls — replays + local judge        │
        └──────┬───────────────────────────────┬───────────────┘
               ▼                               ▼
   ┌────────────────────────────┐  ┌────────────────────────────┐
   │ (6) ROOT-CAUSE / DIFF      │  │ (7) COST-ROUTING BRAIN     │
   │ "git bisect for agents"    │  │ Ollama default, frontier   │
   └────────────────────────────┘  │ APIs opt-in w/ cap         │
                                    └────────────────────────────┘
                               ▼
        ┌──────────────────────────────────────────────────────┐
        │ WEB DASHBOARD (Next.js)                              │
        │ trajectory canvas + reliability surface + diffs      │
        └──────────────────────────────────────────────────────┘
```

## 2. Package → subsystem mapping

| Bible subsystem | Python package | Purpose |
|---|---|---|
| — (shared) | `volo-core` | Domain models (`Recording`, `Step`, `ToolSpec`), interfaces, redaction primitives. Imported by every other package; imports nothing local. |
| (1) Capture | `volo-sdk` | `Recorder`, `record()` ctx manager, framework adapters in `integrations/`. |
| (2) Simulator | `volo-simulator` | `SimulatedEnvironment` ABC; `Tier1Replayer`; (future) `Tier2SourceInformedSim`. |
| (3) Scenarios | `volo-scenarios` | Typed mutation operators applied to a `Recording`. |
| (4) Reliability | `volo-reliability` | Determinism / faithfulness / consistency metrics; report aggregation. |
| (5) Runner | `volo-runner` | Orchestrates: load recording → build sim → for each scenario, run agent → score. Deterministic seed handling. |
| (6) Diff | `volo-diff` | Bisect over recorded steps and over git history to attribute regressions. |
| (7) Models | `volo-models` | Provider abstraction: Ollama by default, frontier APIs behind opt-in. Token + cost cap enforcement. |
| — (entrypoint) | `volo-cli` | Typer CLI tying everything together — the verbs below. |

## 2a. Expansion packages (v1.1 → v2.0)

The seven bible subsystems are the core. The reliability *platform* extends them with additional
packages, each a thin composition over `volo-core` + the simulator, each with its own ADR:

| Package | Milestone / ADR | Purpose |
|---|---|---|
| `volo-mcp` | M10-M11 / ADR-0014, 0015 | Record/replay/fuzz **MCP servers**; `MCPReplayServer`, `volo mcp record\|serve\|fuzz\|conformance`. Un-recorded input → JSON-RPC `-32042` (never hallucinate). |
| `volo-shadow` | M13-M14 / ADR-0017, 0018 | Production **shadow corpus** + nightly **drift sentinel**; `CorpusBank`, `snapshot`/`compare`, `SnapshotHistory`, `volo shadow pull\|adopt\|check\|trend`. |
| `volo-redteam` | M15 / ADR-0019 | Adversarial **attack corpus** (54 probes × 6 classes) + `SafetyAnnex`; canary poison-and-detect, `volo redteam`. |
| `volo-migrate` | M16 / ADR-0020 | **Model-migration lab**: pair two corpora, score reliability + cost delta, `volo migrate`. |
| `volo-personas` | M17 / ADR-0021 | **Simulated users / counterparties**: `PersonaEnvironment` intercepts ask-user tools, `volo persona`. |
| `volo-longhorizon` | M18 / ADR-0022 | **Long-horizon rig**: N-episode replay with memory threaded forward; drift/rot dimensions, `volo horizon`. |
| `pytest-volo` | M12 / ADR-0016 | pytest plugin — the engine behind `@pytest.mark.volo_recording` + fixtures. |

**Framework integrations (M7 + M22):** `integrations/{langgraph, openai_agents, crewai, autogen,
pydantic_ai, semantic_kernel}` — each a thin `wrap()` (proxy swap + `decision` step) +
`import_<fw>_otel()` over the shared `import_otel_trace` seam; duck-typed, deps `volo-core` +
`volo-sdk` only (ADR-0026).

All compose through the same `SimulatedEnvironment` + `current_environment` seam, so nothing above
reaches into another's internals. CLI gate exit codes are distinct: reliability **1**, shadow
drift **3**, red-team **4**, migration-block **5**, persona-goal **6**, horizon-degrade **7**.

**Persistence (M19 / ADR-0023):** `volo_core.persistence` adds gzip-aware `save_recording` /
`load_recording` (transparent on a `.gz` suffix) and a schema-**migration** seam
(`register_migration` → `load_recording` upgrades older recordings before validating). Replay
throughput is benchmarked (`benchmarks/replay_throughput.py`) and guarded above a 10k-steps/min
floor; measured ≫ 5M steps/min.

## 3. Hexagonal layering (bible §7.1)

```
┌─ outer adapters ────────────────────────────────────────────┐
│  FastAPI app · Typer CLI · GitHub Action · Next.js web · OTel│
│            │            │            │            │          │
│            ▼            ▼            ▼            ▼          │
│      ┌────────────────────────────────────────────────┐      │
│      │  application services (runner, recorder, sim) │      │
│      │  packages/volo-{sdk,simulator,runner,…}   │      │
│      └─────────────────────────┬──────────────────────┘      │
│                                ▼                              │
│      ┌────────────────────────────────────────────────┐      │
│      │  domain core: pure types + interfaces          │      │
│      │  packages/volo-core (no I/O, no LLM)       │      │
│      └────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

**Rule:** `volo-core` may not import anything from the other workspace packages. Other
packages depend on core's interfaces, not on each other where avoidable.

## 4. Data flow (the happy path — bible §4.2)

1. Dev wraps their agent with the SDK and runs it once → **`Recording`** (trajectory of spans +
   tool I/O + final output) is saved to `./.volo/recordings/<run_id>.json`.
2. Volo builds a `SimulatedEnvironment` from the recording (+ optional tool specs for higher
   fidelity).
3. Scenario Generator derives N adversarial scenarios from the recording.
4. CI Runner executes the agent against the simulated environment for each scenario,
   deterministically (seeded), with no live model/tool calls.
5. Reliability Engine scores each run on multiple dimensions → a reliability report + surface.
6. Results are diffed against the baseline; regressions fail the build; the dashboard renders.

## 5. Determinism by construction (bible §7.1)

All nondeterminism is isolated behind interfaces in `volo-core`:

- `Clock` (default: `SystemClock`; in CI: `FrozenClock(seed)`).
- `RandomSource` (always seeded; seed recorded in `RunMeta`).
- `ModelProvider` (`OllamaProvider`, `OpenAIProvider`, …; in replay mode, all are replaced with
  `ReplayProvider` that serves cached responses).
- `ToolRegistry` (in replay mode, replaced with the `SimulatedEnvironment`).

Any code path used in CI replay must be pure / seeded. If something can't be made deterministic, it
must be flagged in the `Recording` so the runner knows to mark the scenario as `nondeterministic`
instead of pretending.

## 6. Storage

| Mode | Recordings | Metadata | Artifacts |
|---|---|---|---|
| Local / OSS (default) | `./.volo/recordings/*.json` | SQLite at `./.volo/volo.db` | local FS under `./.volo/artifacts/` |
| Cloud (future) | Cloudflare R2 (S3-compatible, no egress) | Neon/Supabase Postgres | R2 |

Schema migrations: Alembic for Postgres; for SQLite OSS mode, ship schema + lightweight
single-file migrations.

## 7. Open-core boundary (bible §4.3)

| | OSS (Apache-2.0) | Cloud (commercial) |
|---|---|---|
| Capture SDK, CLI, CI runner, Tier-1 simulator, core metrics, local dashboard | ✅ | ✅ |
| Hosted high-fidelity managed simulator | — | ✅ |
| Team collaboration, history, audit | — | ✅ |
| SSO / RBAC | — | ✅ |

Decision recorded in [ADR-0001](./adr/0001-language-and-runtimes.md) (license discussion) — finalize
in a dedicated licensing ADR before opening the repo publicly.

## 8. What we borrowed (bible §3)

Volo studies the existing observability / eval / agent-replay tools openly. The bible's §3
asks us to record what we took from each. Here's the running list:

| Source | What we took | Where it lives |
|---|---|---|
| **DeepEval** (`confident-ai/deepeval`) | pytest-shaped developer ergonomics — evals feel like unit tests. | `tests/test_research_agent_fidelity.py` runs as plain pytest under `-m fidelity`. |
| **Arize Phoenix** (`Arize-ai/phoenix`) | OpenTelemetry as the ingest surface; open-core business model. | `volo_sdk.import_otel_trace` accepts OTLP JSON and JSONL. Open-core boundary documented in §7 above. |
| **LangWatch Scenario** | The record-then-replay pattern + a deterministic-cache layer. | `volo_simulator.Tier1Replayer` is the deterministic cache; `Tier2Replayer` chains synthesis when the cache misses. |
| **MIRAGE** (research) | The "62% naive replay → 99% source-informed" gap is the wedge. | `Tier2Replayer` resolution order: source-informed first, then constrained generation, then flag. ADR-0009 + ADR-0010. |
| **DFAH** (research) | Determinism + faithfulness are uncorrelated — must report both. | `volo_reliability.metrics` ships four orthogonal metrics; aggregator is 5th-percentile by default. |
| **AgentClash** (`agentclash/agentclash`, teammate's repo) | Repo conventions — `docs/`, `docker-compose`, `Makefile`, `.github/workflows/`, a `web/` + `backend/` split. | Mirrored 1:1. We added `docs/STATUS.md` as the live ledger and `docs/sessions/` for narrative notes. |
| **Linear** (frontend reference) | The agent-as-UI-citizen pattern — embed live agent reasoning inside product surfaces. | `apps/web/components/ActivityThread.tsx` renders the agent's reasoning as a console-style thread. |
| **Anthropic.com** (frontend reference) | Editorial serif for headlines + scholarly card treatment for research / changelog. | Instrument Serif on every section heading; `NotesGrid` mirrors Anthropic's research-card layout. |

When we add a new technique or borrow heavily from another tool, we add a row here.

