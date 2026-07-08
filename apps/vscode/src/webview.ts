// Render a Trajectory view model as a self-contained HTML page for the VS Code webview.
// Pure (no `vscode` import) so it is unit-testable. Aesthetic mirrors the dashboard (bible §8).

import { type Trajectory, stepCounts, type TrajectoryStep } from "./trajectory";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const KIND_COLOR: Record<string, string> = {
  model_call: "#4dd0e1",
  tool_call: "#12b886",
  decision: "#f59f00",
  unknown: "#768390",
};

function stepRow(s: TrajectoryStep): string {
  const color = KIND_COLOR[s.kind] ?? "#768390";
  const warn = s.status === "warn" ? ' <span title="no recorded response">⚠</span>' : "";
  return `<li class="step">
    <span class="idx">${String(s.index).padStart(3, "0")}</span>
    <span class="dot" style="background:${color}"></span>
    <span class="kind" style="color:${color}">${escapeHtml(s.kind)}</span>
    <span class="title">${escapeHtml(s.title)}${warn}</span>
  </li>`;
}

export function renderTrajectoryHtml(t: Trajectory): string {
  const counts = stepCounts(t);
  const rows = t.steps.map(stepRow).join("\n");
  const final = escapeHtml(JSON.stringify(t.finalOutput, null, 2) ?? "null");
  const agent = t.agent ? escapeHtml(t.agent) : "—";
  return `<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body{background:#0A0E14;color:#c9d1d9;font:13px/1.6 ui-monospace,Menlo,monospace;padding:1rem}
  h1{font-size:15px;color:#e6edf3;font-weight:600;letter-spacing:-.01em;margin:0 0 .25rem}
  .sub{color:#768390;margin-bottom:1rem}
  ul{list-style:none;margin:0;padding:0;border-left:1px solid #21262d}
  .step{display:flex;gap:.6rem;align-items:baseline;padding:.25rem .5rem}
  .step:hover{background:#0d1117}
  .idx{color:#4b5563;font-size:11px}
  .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
  .kind{min-width:90px;text-transform:uppercase;font-size:11px;letter-spacing:.06em}
  .title{color:#e6edf3}
  pre{background:#0d1117;border:1px solid #21262d;padding:.75rem;overflow:auto;margin-top:1rem}
  .badge{color:#768390}
</style></head><body>
<h1>🛫 ${escapeHtml(t.runId)}</h1>
<div class="sub">framework <b class="badge">${escapeHtml(t.framework)}</b> ·
agent <b class="badge">${agent}</b> ·
${t.steps.length} steps
(<span style="color:${KIND_COLOR.model_call}">${counts.model_call} model</span>,
<span style="color:${KIND_COLOR.tool_call}">${counts.tool_call} tool</span>,
<span style="color:${KIND_COLOR.decision}">${counts.decision} decision</span>${
    counts.warn ? `, <span style="color:#f59f00">${counts.warn} unresolved</span>` : ""
  })</div>
<ul>
${rows}
</ul>
<h1 style="margin-top:1.5rem;font-size:12px">final output</h1>
<pre>${final}</pre>
</body></html>`;
}
