import { describe, expect, it } from "vitest";

import { parseTrajectory, stepCounts } from "./trajectory";
import { renderTrajectoryHtml } from "./webview";

const RECORDING = {
  run_id: "run-abc",
  agent_meta: { framework: "mcp", agent_name: "support-bot" },
  steps: [
    { payload: { type: "decision", label: "route", chosen: "search" } },
    {
      payload: {
        type: "tool_call",
        tool: "mcp.tool:search",
        request: { q: "x" },
        response: { hits: 3 },
      },
    },
    { payload: { type: "model_call", provider: "ollama", model: "llama3.2:3b", response: null } },
  ],
  final_output: { answer: "3 hits" },
};

describe("parseTrajectory", () => {
  it("maps steps to a view model", () => {
    const t = parseTrajectory(JSON.stringify(RECORDING));
    expect(t.runId).toBe("run-abc");
    expect(t.framework).toBe("mcp");
    expect(t.agent).toBe("support-bot");
    expect(t.steps.map((s) => s.kind)).toEqual(["decision", "tool_call", "model_call"]);
    expect(t.steps[0].title).toBe("route → search");
    expect(t.steps[1].title).toBe("mcp.tool:search");
  });

  it("flags a call with no recorded response as a warning", () => {
    const t = parseTrajectory(RECORDING);
    expect(t.steps[1].status).toBe("ok"); // tool call has a response
    expect(t.steps[2].status).toBe("warn"); // model call has response: null
  });

  it("tolerates a minimal / empty recording", () => {
    const t = parseTrajectory({ run_id: "r" });
    expect(t.steps).toEqual([]);
    expect(t.framework).toBe("unknown");
    expect(t.agent).toBeNull();
  });

  it("counts steps by kind", () => {
    const c = stepCounts(parseTrajectory(RECORDING));
    expect(c).toMatchObject({ model_call: 1, tool_call: 1, decision: 1, warn: 1 });
  });
});

describe("renderTrajectoryHtml", () => {
  it("produces self-contained HTML with the run id and steps", () => {
    const html = renderTrajectoryHtml(parseTrajectory(RECORDING));
    expect(html.startsWith("<!doctype html>")).toBe(true);
    expect(html).toContain("run-abc");
    expect(html).toContain("mcp.tool:search");
    expect(html).toContain("3 hits");
  });

  it("escapes HTML in step content", () => {
    const evil = parseTrajectory({
      run_id: "r",
      steps: [{ payload: { type: "tool_call", tool: "<script>alert(1)</script>", response: {} } }],
    });
    const html = renderTrajectoryHtml(evil);
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).toContain("&lt;script&gt;");
  });
});
