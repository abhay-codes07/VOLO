# Volo — VS Code extension

Inspect Volo agent recordings without leaving the editor: open a `.volo/recordings/*.json` as a
**trajectory view**, and **replay** it against the deterministic simulator in one click.

## Commands

- **Volo: Open Trajectory View** — renders the recording as a step-by-step flight path (model
  calls, tool calls, decisions), flags any step with no recorded response, and shows the final
  output. Available from the command palette or the explorer right-click menu on a `.json` file.
- **Volo: Replay Recording (volo sim)** — runs `uv run volo sim <file>` in an integrated terminal,
  so it works with whatever Python env the workspace already uses.

## Layout

- `src/trajectory.ts` — pure parse of a Recording JSON into a view model (no `vscode` import).
- `src/webview.ts` — pure render of the view model to self-contained HTML.
- `src/extension.ts` — thin VS Code glue (the only file that imports `vscode`).

The pure modules are unit-tested with vitest (`npm test`); `npm run build` compiles the extension
with `tsc`.

## Develop

```bash
cd apps/vscode
npm install
npm test          # vitest — parse + render logic
npm run typecheck # tsc --noEmit
npm run build     # -> dist/extension.js
```

Then press F5 in VS Code (with this folder open) to launch an Extension Development Host.
