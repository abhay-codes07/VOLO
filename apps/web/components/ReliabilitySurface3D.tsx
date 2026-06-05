"use client";

import { motion, useInView } from "motion/react";
import { useRef } from "react";
import type { ReliabilityReport } from "@/lib/api";

/**
 * Isometric 3D reliability surface. Each cell of the (scenario × metric) grid is an extruded
 * bar with height proportional to the metric score. Renders as pure SVG — no three.js, no
 * runtime canvas painting, just transforms.
 */

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

function colorFor(v: number): { top: string; side: string; front: string } {
  // semantic banding
  if (v >= 0.9) return {
    top:   "#3DE0B8",
    side:  "#1E8C72",
    front: "#26B594",
  };
  if (v >= 0.6) return {
    top:   "#F6B73C",
    side:  "#9E7220",
    front: "#C8902C",
  };
  return {
    top:   "#FF5C6C",
    side:  "#993742",
    front: "#CC4854",
  };
}

// Isometric projection — 2:1 tile
const TILE_W = 80;
const TILE_H = 40;
const SCALE = 70;       // pixels per unit of metric value
const MARGIN = 60;

function iso(gx: number, gy: number): { sx: number; sy: number } {
  return {
    sx: (gx - gy) * (TILE_W / 2),
    sy: (gx + gy) * (TILE_H / 2),
  };
}

export function ReliabilitySurface3D({ report }: { report: ReliabilityReport | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-50px" });

  if (!report || report.scenarios.length === 0) {
    return (
      <div className="hairline bg-surface-1 p-12 text-center font-mono text-sm text-text-mute">
        reliability surface — no report loaded
      </div>
    );
  }

  const rows = report.scenarios.length;          // y-axis (scenarios)
  const cols = METRIC_KEYS.length;               // x-axis (metrics)

  // Compute SVG bounds.
  const corners = [
    iso(0, 0), iso(cols, 0), iso(0, rows), iso(cols, rows),
  ];
  const minX = Math.min(...corners.map((c) => c.sx)) - MARGIN;
  const maxX = Math.max(...corners.map((c) => c.sx)) + MARGIN;
  const minY = Math.min(...corners.map((c) => c.sy)) - MARGIN - SCALE;
  const maxY = Math.max(...corners.map((c) => c.sy)) + MARGIN + 30;
  const width = maxX - minX;
  const height = maxY - minY;

  // Build cells — sort back-to-front for proper painter's-algorithm overlap.
  type Cell = { row: number; col: number; v: number; depth: number };
  const cells: Cell[] = [];
  report.scenarios.forEach((sc, r) => {
    METRIC_KEYS.forEach((m, c) => {
      const v = sc.metrics[m] ?? 0;
      cells.push({ row: r, col: c, v, depth: r + c });
    });
  });
  cells.sort((a, b) => a.depth - b.depth);

  return (
    <div
      ref={ref}
      className="hairline bg-surface-1 shadow-elev-1 overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-3 border-b border-border-1 bg-surface-2/40">
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute">
          reliability surface · isometric · 7 × 4
        </div>
        <div className="font-mono text-[11px] text-text-mute">
          higher cells = healthier metric
        </div>
      </div>

      <div className="relative">
        <svg
          viewBox={`${minX} ${minY} ${width} ${height}`}
          className="block w-full"
          style={{ maxHeight: 540 }}
        >
          <defs>
            <linearGradient id="floor-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="rgba(255,255,255,0.04)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.0)" />
            </linearGradient>
          </defs>

          {/* floor grid */}
          {Array.from({ length: rows + 1 }).map((_, r) => {
            const a = iso(0, r);
            const b = iso(cols, r);
            return (
              <line
                key={`gx-${r}`}
                x1={a.sx} y1={a.sy} x2={b.sx} y2={b.sy}
                stroke="rgba(255,255,255,0.07)"
                strokeWidth={1}
              />
            );
          })}
          {Array.from({ length: cols + 1 }).map((_, c) => {
            const a = iso(c, 0);
            const b = iso(c, rows);
            return (
              <line
                key={`gy-${c}`}
                x1={a.sx} y1={a.sy} x2={b.sx} y2={b.sy}
                stroke="rgba(255,255,255,0.07)"
                strokeWidth={1}
              />
            );
          })}

          {/* metric axis labels (front edge — row 0 / top) */}
          {METRIC_KEYS.map((m, c) => {
            const p = iso(c + 0.5, 0);
            return (
              <text
                key={`mx-${c}`}
                x={p.sx}
                y={p.sy - 10}
                textAnchor="middle"
                fill="var(--text-mute)"
                fontFamily="var(--font-mono)"
                fontSize="10"
                style={{ textTransform: "uppercase", letterSpacing: "0.12em" }}
              >
                {METRIC_LABEL[m]}
              </text>
            );
          })}
          {/* scenario axis labels (right edge — col last) */}
          {report.scenarios.map((sc, r) => {
            const p = iso(cols, r + 0.5);
            return (
              <text
                key={`my-${r}`}
                x={p.sx + 12}
                y={p.sy + 4}
                fill="var(--text-mute)"
                fontFamily="var(--font-mono)"
                fontSize="10"
                style={{ letterSpacing: "0.04em" }}
              >
                {sc.scenario_op}
              </text>
            );
          })}

          {/* extruded bars */}
          {cells.map(({ row, col, v }, i) => {
            const c = colorFor(v);
            const lift = v * SCALE;
            // four bottom corners
            const blf = iso(col, row);
            const brf = iso(col + 1, row);
            const blb = iso(col, row + 1);
            const brb = iso(col + 1, row + 1);
            // top corners (lifted up by `lift` along screen Y)
            const tlf = { sx: blf.sx, sy: blf.sy - lift };
            const trf = { sx: brf.sx, sy: brf.sy - lift };
            const tlb = { sx: blb.sx, sy: blb.sy - lift };
            const trb = { sx: brb.sx, sy: brb.sy - lift };
            const delay = i * 0.04;
            return (
              <motion.g
                key={`cell-${row}-${col}`}
                initial={{ opacity: 0, y: -12 }}
                animate={inView ? { opacity: 1, y: 0 } : { opacity: 0 }}
                transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
              >
                {/* left side (front-left face) */}
                <polygon
                  points={`${blf.sx},${blf.sy} ${tlf.sx},${tlf.sy} ${trf.sx},${trf.sy} ${brf.sx},${brf.sy}`}
                  fill={c.front}
                  stroke="rgba(0,0,0,0.25)"
                  strokeWidth={0.5}
                />
                {/* right side */}
                <polygon
                  points={`${brf.sx},${brf.sy} ${trf.sx},${trf.sy} ${trb.sx},${trb.sy} ${brb.sx},${brb.sy}`}
                  fill={c.side}
                  stroke="rgba(0,0,0,0.25)"
                  strokeWidth={0.5}
                />
                {/* top */}
                <polygon
                  points={`${tlf.sx},${tlf.sy} ${trf.sx},${trf.sy} ${trb.sx},${trb.sy} ${tlb.sx},${tlb.sy}`}
                  fill={c.top}
                  stroke="rgba(255,255,255,0.18)"
                  strokeWidth={0.5}
                />
                {/* value label on top */}
                <text
                  x={(tlf.sx + trb.sx) / 2}
                  y={(tlf.sy + trb.sy) / 2 + 3}
                  textAnchor="middle"
                  fill="rgba(0,0,0,0.85)"
                  fontFamily="var(--font-mono)"
                  fontSize="9"
                  fontWeight="600"
                  style={{ pointerEvents: "none" }}
                >
                  {v.toFixed(2)}
                </text>
              </motion.g>
            );
          })}
        </svg>
      </div>

      {/* legend */}
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
