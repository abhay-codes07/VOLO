# Volo — top-level developer shortcuts.
# All targets are idempotent. The Makefile is the contributor-facing entrypoint;
# deeper docs live in package READMEs.

.DEFAULT_GOAL := help

# ---------- meta ----------
.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------- environment ----------
.PHONY: setup
setup: ## Install Python + JS toolchains (uv + pnpm), sync deps.
	uv python install 3.12
	uv sync --all-packages
	corepack enable pnpm || true
	pnpm install --frozen-lockfile || pnpm install

# ---------- dev ----------
.PHONY: dev
dev: ## Bring up the local dev stack (api + web).
	@echo "→ start FastAPI + Next.js in parallel (Ctrl+C to stop both)"
	@$(MAKE) -j 2 dev-api dev-web

.PHONY: dev-api
dev-api: ## Run the FastAPI service locally.
	uv run --package volo-api uvicorn volo_api.main:app --reload --port 8080

.PHONY: dev-web
dev-web: ## Run the Next.js dashboard locally.
	pnpm --filter web dev

# ---------- quality ----------
.PHONY: test
test: ## Run all Python and JS tests.
	uv run pytest
	pnpm -r --if-present test

.PHONY: lint
lint: ## Lint Python and JS.
	uv run ruff check .
	uv run ruff format --check .
	pnpm -r --if-present lint

.PHONY: format
format: ## Auto-format Python and JS.
	uv run ruff format .
	uv run ruff check --fix .
	pnpm -r --if-present format

.PHONY: typecheck
typecheck: ## Type-check Python (mypy) and JS (tsc).
	uv run mypy
	pnpm -r --if-present typecheck

# ---------- volo CLI ----------
.PHONY: volo
volo: ## Run the volo CLI (forward args: `make volo ARGS="record --help"`).
	uv run volo $(ARGS)

# ---------- githooks ----------
.PHONY: githooks
githooks: ## Install repo-local git hooks (.githooks/) into git's hooks path.
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit || true
	@echo "→ hooks installed at .githooks/. Run a commit to verify."

# ---------- housekeeping ----------
.PHONY: clean
clean: ## Remove build + cache artifacts.
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf apps/web/.next apps/web/node_modules
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
