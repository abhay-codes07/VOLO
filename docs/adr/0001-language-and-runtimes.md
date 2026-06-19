# ADR 0001: Language choice & runtime management

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §5

## Context
We need to pick the primary language for the core engine, SDK, and CLI, plus the runtime manager.
The product instruments AI agents — the agent ecosystem (LangGraph, OpenAI Agents SDK, CrewAI,
DeepEval, Phoenix) is overwhelmingly Python-first. The web dashboard is a separate concern and is
naturally TypeScript.

## Decision
- **Core engine / SDK / CLI / API:** Python **3.12+**, managed via **`uv`** (Astral).
- **Web dashboard:** TypeScript + Next.js (App Router).
- **License (confirmed 2026-05-31):** **Apache-2.0** for the OSS core (this repo). A future
  top-level `cloud/` directory will be under a separate **commercial license** (Phoenix /
  Sentry pattern). Until cloud code lands, the boundary is hypothetical — the boundary moment
  itself will get its own ADR once we draft the commercial terms.

System Python on the dev box is 3.10. We pin 3.12 via `uv python install 3.12` and never call
`python` directly — only `uv run`.

## Consequences
- **Easy:** integration with existing agent frameworks; large library ecosystem (Pydantic, FastAPI,
  Typer, OTel, pytest, Ruff, mypy).
- **Hard:** if we later want to ship a single static binary, we'd need PyOxidizer / shiv / similar.
  Acceptable trade — agent users already have Python.
- **Committed to:** Pydantic v2, SQLModel (or SQLAlchemy 2.0), OTel SDK as instrumentation surface,
  Typer for CLI, FastAPI for the API service. Each gets its own ADR if we ever swap.

## Alternatives considered
- **TypeScript core** — would unify with the dashboard, but cuts us off from most of the agent
  ecosystem and the eval / OTel tooling. Rejected.
- **Poetry / pip** — slower, less reproducible, weaker workspace support. Rejected in favor of `uv`.
- **Rust core with Python bindings** — overkill at MVP; revisit if the simulator becomes
  performance-critical.
