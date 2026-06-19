# Contributing to Volo

Thanks for your interest in Volo — a flight simulator for AI agents. This guide covers local
setup, the test/lint loop, and the conventions we hold the codebase to.

By contributing you agree that your contributions are licensed under the project's
[Apache-2.0 License](LICENSE).

## Prerequisites

- **Python 3.12+** — the system Python may be older; we pin via [uv](https://docs.astral.sh/uv/).
- **Node 20+** — for the `apps/web` dashboard.
- **uv** — `pip install uv` (or see the uv docs). Manages the Python workspace and the venv.
- *(optional)* **Docker** — for the one-command container stack (`docker compose up`).
- *(optional)* **Ollama** — for local LLM judges / Tier-2 tool synthesis.

## Setup

```bash
make setup        # install toolchains + sync all workspace deps
make dev          # bring up the local stack (api on :8080, web on :3001)
```

Or drive the CLI directly:

```bash
uv run volo --help          # record / sim / scenarios / run / ci / diff / init / demo
uv run volo init            # 60-second quickstart: record + score one run
```

## The inner loop

Everything must be green before you open a PR:

```bash
make test         # pytest (Python) + vitest (web)
make lint         # ruff + mypy (Python) + eslint + tsc (web)
make format       # ruff-format + prettier — run before committing
make typecheck    # mypy (strict, whole monorepo) + tsc
```

Python typing is **strict** across the whole monorepo (`[tool.mypy] strict = true`). Every
workspace package ships a `py.typed` marker, so cross-package imports are type-checked — keep
them that way.

**Tests ship with code, not after.** A change without a test for the behaviour it adds or fixes
is incomplete.

## Repo shape

```
packages/      # 9 Python packages (uv workspace): volo-{core,sdk,simulator,scenarios,
               #   reliability,runner,diff,models,cli}
services/api   # FastAPI service (volo-api)
apps/web       # Next.js dashboard
integrations/  # framework adapters (langgraph / openai-agents / crewai)
examples/      # runnable example agents
benchmarks/    # public Tier-2 fidelity benchmark
docs/          # architecture, roadmap, ADRs, status ledger
website/       # Mintlify documentation site
```

## Commits & PRs

- **Conventional Commits** — `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
- **Small, reviewable commits** — one logical change each. Narrow and deep beats broad and shallow.
- **Branch off `main`** and open a PR. CI runs lint, typecheck, tests, and a reliability
  self-check; the example workflow also posts a reliability summary as a PR comment.
- Don't invent library behavior — check the installed package or real docs.

## Architectural decisions

Non-trivial or one-way-door decisions are recorded as ADRs in [`docs/adr/`](docs/adr/). If your
change makes such a decision, add `docs/adr/NNNN-title.md` (copy the format of an existing one)
in the same PR. System architecture is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), the
milestone plan in [`docs/ROADMAP.md`](docs/ROADMAP.md), and domain terms / metric definitions in
[`docs/GLOSSARY.md`](docs/GLOSSARY.md).

## Reporting bugs & security issues

- **Bugs / features** — open a GitHub issue with repro steps.
- **Security vulnerabilities** — please do **not** open a public issue. See [SECURITY.md](SECURITY.md).
