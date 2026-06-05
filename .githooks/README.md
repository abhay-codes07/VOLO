# `.githooks/`

Per-repo git hooks (bible §7.2). Installed into `.git/hooks/` via:

```bash
make githooks
```

That command points git at this directory by setting `core.hooksPath`, so every contributor
runs the same hooks without copy-paste.

Today: just `pre-commit`. The hook runs ruff lint + format check, mypy on the core
domain, and the fast pytest slice. CI is the source of truth for the broader test suite.
