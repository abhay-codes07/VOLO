"use client";

import { Group } from "@visx/group";
import { HeatmapRect } from "@visx/heatmap";
import { scaleLinear } from "@visx/scale";
import type { ReliabilityReport } from "@/lib/api";

const METRIC_KEYS = [
  "trajectory_determinism",
  "decision_determinism",
  "faithfulness",
  "consistency_under_repetition",
] as const;

const METRIC_LABEL: Record<(typeof METRIC_KEYS)[number], string> = {
  trajectory_determinism:        "trajectory",
  decision_determinism:          "decision",
  faithfulness:                  "faithful",
  consistency_under_repetition:  "consistency",
};

type Bucket = { bin: number; count: number };
type Column = { bin: number; bins: Bucket[] };

function rectColor(v: number): string {
  if (v >= 0.9) return "#3DE0B8";
  if (v >= 0.6) return "#F6B73C";
  return "#FF5C6C";
}

/**
 * Visx-powered reliability heatmap — same data as `ReliabilityHeatmap` but with proper
 * scales, axis labels, and a tooltip-friendly DOM structure.
 */
export function ReliabilityHeatmapVisx({ report }: { report: ReliabilityReport | null }) {
  if (!report || report.scenarios.length === 0) {
    return (
      <div className="hairline bg-surface-1 p-12 text-center font-mono text-sm text-text-mute">
        reliability surface — no report loaded
      </div>
    );
  }

  const width = 720;
  const height = Math.max(160, report.scenarios.length * 44 + 80);
  const margin = { top: 40, right: 24, bottom: 24, left: 200 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  // Build column-major data: one column per metric.
  const columns: Column[] = METRIC_KEYS.map((metric, mIdx) => ({
    bin: mIdx,
    bins: report.scenarios.map((sc, sIdx) => ({
      bin: sIdx,
      count: sc.metrics[metric] ?? 0,
    })),
  }));

  const binWidth = innerW / METRIC_KEYS.length;
  const binHeight = innerH / report.scenarios.length;

  const xScale = scaleLinear<number>({
    domain: [0, METRIC_KEYS.length],
    range: [0, innerW],
  });
  const yScale = scaleLinear<number>({
    domain: [0, report.scenarios.length],
    range: [0, innerH],
  });

  return (
    <div className="hairline bg-surface-1 shadow-elev-1 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
          reliability surface · visx
        </div>
        <div
          className={
            report.verdict === "ship" ? "chip chip-nominal" : "chip chip-failure"
          }
        >
          verdict {report.verdict.replace("_", " ")}
        </div>
      </div>

      <svg width={width} height={height} className="block w-full">
        {/* metric column labels */}
        <Group left={margin.left} top={margin.top - 14}>
          {METRIC_KEYS.map((m, i) => (
            <text
              key={m}
              x={i * binWidth + binWidth / 2}
              y={0}
              textAnchor="middle"
              fill="var(--text-mute)"
              fontFamily="var(--font-mono)"
              fontSize={10}
              style={{ textTransform: "uppercase", letterSpacing: "0.12em" }}
            >
              {METRIC_LABEL[m]}
            </text>
          ))}
        </Group>

        {/* scenario row labels */}
        <Group top={margin.top}>
          {report.scenarios.map((sc, i) => (
            <text
              key={sc.scenario_op + sc.seed}
              x={margin.left - 10}
              y={i * binHeight + binHeight / 2 + 4}
              textAnchor="end"
              fill="var(--text-lo)"
              fontFamily="var(--font-mono)"
              fontSize={11}
            >
              {sc.scenario_op}
            </text>
          ))}
        </Group>

        <Group left={margin.left} top={margin.top}>
          <HeatmapRect<Column, Bucket>
            data={columns}
            xScale={(v) => xScale(v) ?? 0}
            yScale={(v) => yScale(v) ?? 0}
            colorScale={(v) => rectColor(Number(v))}
            opacityScale={(v) => 0.5 + Math.min(1, Math.max(0, Number(v))) * 0.45}
            binWidth={binWidth - 2}
            binHeight={binHeight - 2}
            gap={2}
          >
            {(rects) =>
              rects.map((cols) =>
                cols.map((rect) => (
                  <g key={`r-${rect.row}-${rect.column}`}>
                    <rect
                      x={rect.x}
                      y={rect.y}
                      width={rect.width}
                      height={rect.height}
                      fill={rect.color}
                      fillOpacity={rect.opacity}
                      stroke="rgba(0,0,0,0.25)"
                    />
                    <text
                      x={rect.x + rect.width / 2}
                      y={rect.y + rect.height / 2 + 4}
                      textAnchor="middle"
                      fill="rgba(0,0,0,0.85)"
                      fontFamily="var(--font-mono)"
                      fontSize={11}
                      fontWeight={600}
                    >
                      {(rect.bin?.count ?? 0).toFixed(2)}
                    </text>
                  </g>
                )),
              )
            }
          </HeatmapRect>
        </Group>
      </svg>

      <div className="border-t border-border-1 px-5 py-3 font-mono text-[11px] text-text-mute flex items-center gap-5">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#3DE0B8" }} /> ≥ 0.90 ship
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#F6B73C" }} /> ≥ 0.60 warn
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#FF5C6C" }} /> &lt; 0.60 fail
        </span>
      </div>
    </div>
  );
}
