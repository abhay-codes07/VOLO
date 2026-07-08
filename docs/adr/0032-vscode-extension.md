# ADR 0032: the VS Code extension keeps parse/render pure; glue is the only `vscode`-coupled file

- Status: accepted
- Date: 2026-07-08

## Context

M23 (newplan P8, dev surface) adds a VS Code extension to inspect recordings as trajectory views
and replay them. It's the repo's first TypeScript/editor surface; the concern is testability — a
VS Code extension normally needs the heavyweight `@vscode/test-electron` host to test anything,
which doesn't fit this Python-centric repo's fast test loop.

## Decision

1. **Separate pure logic from `vscode` glue.** `src/trajectory.ts` (parse a Recording JSON into a
   view model) and `src/webview.ts` (render that view model to self-contained HTML) import nothing
   from `vscode`, so they run under plain **vitest** — the same toolchain `apps/web` already uses.
   `src/extension.ts` is the only file that imports `vscode`, and it is a thin adapter: pick a
   file, read it, call the pure functions, open a webview / send a terminal command. It carries no
   logic worth unit-testing.
2. **Replay reuses the CLI, not a reimplementation.** "Replay Recording" runs `uv run volo sim
   <file>` in an integrated terminal, so it inherits whatever Python env the workspace uses and
   stays correct as the simulator evolves — the extension never forks replay behavior.
3. **The webview is static and script-disabled.** `createWebviewPanel(..., { enableScripts:
   false })` and all interpolated content is HTML-escaped in `webview.ts` (tested), so a malicious
   recording can't inject script into the panel.
4. **No build coupling to the Python workspace.** `apps/vscode` is its own npm package (tsc +
   vitest), git-ignoring `node_modules`/`dist`. It is not wired into the Python `uv`/pytest CI;
   its tests run via `npm test`, mirroring `apps/web`.

## Consequences

- The valuable logic (parsing the recording schema, rendering, escaping) is covered by fast unit
  tests with no editor host; the untested surface is the ~40-line `vscode` adapter, which is the
  standard, acceptable line for extension code.
- Reusing `volo sim` means the extension can't replay in a sandbox that lacks the CLI — but that's
  the same `uv` the rest of the workflow needs, so it's not a new requirement.
- Keeping the panel script-free trades interactivity (no client-side filtering yet) for safety and
  simplicity; a future richer canvas can add scripts with a strict CSP if needed.
- The extension is unpublished (no marketplace account); it runs from source via F5 / a packaged
  `.vsix`. Publishing is a later, non-code step.

## Alternatives considered

- **Render the trajectory inside the existing Next.js dashboard and just deep-link from VS Code** —
  rejected: the point is to inspect a local recording file *in the editor* without running the web
  app; a self-contained webview needs no server.
- **Full `@vscode/test-electron` integration tests** — rejected for now: heavy, slow, and it would
  only cover the thin glue; extracting the logic gets the real coverage for a fraction of the cost.
- **Reimplement replay in TypeScript** — rejected: forks the simulator; shelling to `volo sim`
  keeps one source of truth.
