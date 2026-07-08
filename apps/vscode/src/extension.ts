// VS Code extension entrypoint — thin glue over the pure parse/render logic (M23).
// The `vscode` import lives only here; trajectory.ts / webview.ts stay testable in plain Node.

import * as fs from "fs";
import * as vscode from "vscode";

import { parseTrajectory } from "./trajectory";
import { renderTrajectoryHtml } from "./webview";

async function pickRecordingUri(): Promise<vscode.Uri | undefined> {
  const active = vscode.window.activeTextEditor?.document.uri;
  if (active && active.fsPath.endsWith(".json")) return active;
  const picked = await vscode.window.showOpenDialog({
    canSelectMany: false,
    filters: { "Volo recording": ["json"] },
    openLabel: "Open trajectory",
  });
  return picked?.[0];
}

function openTrajectory(uri: vscode.Uri): void {
  let trajectory;
  try {
    trajectory = parseTrajectory(fs.readFileSync(uri.fsPath, "utf8"));
  } catch (err) {
    void vscode.window.showErrorMessage(`Volo: could not read recording — ${String(err)}`);
    return;
  }
  const panel = vscode.window.createWebviewPanel(
    "voloTrajectory",
    `Volo · ${trajectory.runId}`,
    vscode.ViewColumn.Beside,
    { enableScripts: false },
  );
  panel.webview.html = renderTrajectoryHtml(trajectory);
}

function replayRecording(uri: vscode.Uri): void {
  // Replay against the deterministic simulator — reuses the CLI, so it works with whatever
  // Python env the workspace already uses.
  const terminal = vscode.window.createTerminal("volo sim");
  terminal.show();
  terminal.sendText(`uv run volo sim "${uri.fsPath}"`);
}

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("volo.openTrajectory", async (uri?: vscode.Uri) => {
      const target = uri ?? (await pickRecordingUri());
      if (target) openTrajectory(target);
    }),
    vscode.commands.registerCommand("volo.replayRecording", async (uri?: vscode.Uri) => {
      const target = uri ?? (await pickRecordingUri());
      if (target) replayRecording(target);
    }),
  );
}

export function deactivate(): void {
  /* nothing to clean up */
}
