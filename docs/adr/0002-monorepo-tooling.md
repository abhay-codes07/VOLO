# ADR 0002: Monorepo tooling

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §6, ADR-0001

## Context
We have 9 Python packages, 1 FastAPI service, 1 Next.js app, an integrations dir, and an examples
dir. We need a coherent build/test/lint experience without overengineering.

## Decision
- **Python workspace:** `uv` workspaces declared in the root `pyproject.toml`. Each package lives
  in `packages/<name>/` with its own `pyproject.toml`. Internal deps use `tool.uv.sources` with
  `workspace = true`.
- **JS workspace:** **pnpm** workspaces declared in root `package.json` (`workspaces` field) plus
  `pnpm-workspace.yaml`. **Turborepo** orchestrates JS tasks.
- **Top-level shortcuts:** a `Makefile` exposes `make dev | test | lint | build` so contributors
  don't need to learn both toolchains on day one.
- **CI:** GitHub Actions, separate jobs per language, matrix on the Python side.

## Consequences
- Two package managers in one repo (uv + pnpm). Acceptable — they don't overlap and each is best
  in class for its language.
- The Makefile is the single contributor-facing entrypoint; deeper docs live in the relevant
  package READMEs.
- Turborepo caching applies to JS only; uv has its own cache that "just works" via `uv sync`.

## Alternatives considered
- **Bazel / Pants** — overkill at our scale; high contributor onboarding cost.
- **Nx** — JS-centric, weaker Python story.
- **A single Python-only monorepo, dashboard in a separate repo** — fragments the OSS story,
  hurts dogfood, makes the CI dashboard awkward. Rejected.
