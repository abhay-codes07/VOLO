"use client";

import { motion, useInView } from "motion/react";
import { useMemo, useRef, useState } from "react";
import type { Step } from "@/lib/api";

type Node = {
  id: string;
  index: number;
  x: number;
  y: number;
  type: Step["payload"]["type"];
  label: string;
  step: Step;
};
type Edge = { from: string; to: string };

const NODE_COLOR: Record<Step["payload"]["type"], string> = {
  model_call: "var(--signal-info)",
  tool_call:  "var(--signal-nominal)",
  decision:   "var(--signal-warning)",
};

const NODE_KIND_LABEL: Record<Step["payload"]["type"], string> = {
  model_call: "model",
  tool_call:  "tool",
  decision:   "decision",
};

function briefLabel(step: Step): string {
  const p = step.payload;
  if (p.type === "model_call") return `${p.provider}/${p.model}`;
  if (p.type === "tool_call")  return p.tool;
  return p.label;
}

export function TrajectoryCanvas({
  steps,
  highlight,
  height = 280,
  failureIndex,
}: {
  steps: Step[];
  highlight?: number;
  height?: number;
  failureIndex?: number | null;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const inView = useInView(containerRef, { once: true, margin: "-30px" });

  const layout = useMemo(() => {
    if (steps.length === 0) return { nodes: [] as Node[], edges: [] as Edge[], width: 600 };
    const marginX = 56;
    const slot = 110;
    const width = marginX * 2 + Math.max(0, steps.length - 1) * slot;
    const cy = height / 2;
    const wave = Math.min(28, height / 8);
    const nodes: Node[] = steps.map((s, i) => ({
      id: s.step_id,
      index: i,
      x: marginX + i * slot,
      y: cy + (i % 2 === 1 ? wave : -wave),
      type: s.payload.type,
      label: briefLabel(s),
      step: s,
    }));
    const idToIdx = new Map(nodes.map((n) => [n.id, n.index]));
    const edges: Edge[] = [];
    nodes.forEach((n, i) => {
      const parent = n.step.parent_id;
      if (parent && idToIdx.has(parent)) {
        edges.push({ from: parent, to: n.id });
      } else if (i > 0) {
        edges.push({ from: nodes[i - 1].id, to: n.id });
      }
    });
    return { nodes, edges, width };
  }, [steps, height]);

  if (steps.length === 0) {
    return (
      <div className="hairline bg-surface-1 p-10 text-center">
        <p className="text-text-mute text-sm font-mono">trajectory canvas — no recording</p>
      </div>
    );
  }

  const idToNode = new Map(layout.nodes.map((n) => [n.id, n]));
  const active = hover ?? highlight ?? null;
  const activeStep = active !== null ? layout.nodes[active] : null;

  // sequential draw timing
  const EDGE_BASE = 0.15;
  const EDGE_STEP = 0.12;
  const NODE_BASE = 0.05;
  const NODE_STEP = 0.12;

  return (
    <div ref={containerRef} className="hairline bg-surface-1 overflow-hidden">
      <svg
        viewBox={`0 0 ${layout.width} ${height}`}
        className="block w-full"
        style={{ height }}
        role="img"
        aria-label="agent trajectory"
      >
        <defs>
          <pattern id={`grid-${layout.width}`} width="22" height="22" patternUnits="userSpaceOnUse">
            <path d="M 22 0 L 0 0 0 22" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
          </pattern>
          <radialGradient id="bg-glow" cx="50%" cy="50%" r="60%">
            <stop offset="0%"   stopColor="rgba(111,170,255,0.10)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.5" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <rect width={layout.width} height={height} fill={`url(#grid-${layout.width})`} />
        <rect width={layout.width} height={height} fill="url(#bg-glow)" />

        {layout.edges.map((e, i) => {
          const a = idToNode.get(e.from)!;
          const b = idToNode.get(e.to)!;
          const mx = (a.x + b.x) / 2;
          const path = `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
          const isFailEdge =
            failureIndex !== undefined &&
            failureIndex !== null &&
            (a.index === failureIndex || b.index === failureIndex);
          return (
            <motion.path
              key={i}
              d={path}
              fill="none"
              stroke={isFailEdge ? "var(--signal-failure)" : "var(--border-2)"}
              strokeWidth={isFailEdge ? 2 : 1.25}
              opacity={isFailEdge ? 0.95 : 0.6}
              initial={{ pathLength: 0 }}
              animate={inView ? { pathLength: 1 } : { pathLength: 0 }}
              transition={{ duration: 0.55, delay: EDGE_BASE + i * EDGE_STEP, ease: [0.16, 1, 0.3, 1] }}
            />
          );
        })}

        {layout.nodes.map((n) => {
          const isFail =
            failureIndex !== undefined && failureIndex !== null && n.index === failureIndex;
          const isActive = active === n.index;
          const stroke = isFail ? "var(--signal-failure)" : NODE_COLOR[n.type];
          const fill = isActive ? stroke : "var(--surface-2)";
          const r = isFail ? 14 : 11;
          return (
            <motion.g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              onMouseEnter={() => setHover(n.index)}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "pointer", transformOrigin: `${n.x}px ${n.y}px` }}
              initial={{ scale: 0, opacity: 0 }}
              animate={inView ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
              transition={{
                duration: 0.55,
                delay: NODE_BASE + n.index * NODE_STEP,
                type: "spring",
                stiffness: 240,
                damping: 18,
              }}
              data-cursor="hover"
            >
              {isFail && (
                <motion.circle
                  r={r + 6}
                  fill="none"
                  stroke="var(--signal-failure)"
                  strokeWidth={1.5}
                  opacity={0.5}
                  animate={{ scale: [1, 1.6, 1], opacity: [0.6, 0, 0.6] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
                />
              )}
              <motion.circle
                r={r}
                fill={fill}
                stroke={stroke}
                strokeWidth={2}
                filter={isFail ? "url(#node-glow)" : undefined}
                whileHover={{ scale: 1.18 }}
                transition={{ type: "spring", stiffness: 260, damping: 18 }}
              />
              <text
                y={r + 14}
                textAnchor="middle"
                fill="var(--text-lo)"
                fontFamily="var(--font-mono)"
                fontSize="10"
                style={{ pointerEvents: "none" }}
              >
                {NODE_KIND_LABEL[n.type]}
              </text>
              <text
                y={-r - 8}
                textAnchor="middle"
                fill="var(--text-mute)"
                fontFamily="var(--font-mono)"
                fontSize="9"
                style={{ pointerEvents: "none" }}
              >
                {String(n.index + 1).padStart(3, "0")}
              </text>
            </motion.g>
          );
        })}
      </svg>

      <div className="border-t border-border-1 px-5 py-3 font-mono text-[11px]">
        {activeStep ? (
          <motion.div
            key={activeStep.index}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="grid grid-cols-1 md:grid-cols-4 gap-3 text-text-lo"
          >
            <div>
              <div className="text-text-mute uppercase tracking-widest text-[10px]">step</div>
              <div className="text-text-hi mt-0.5">
                #{String(activeStep.index + 1).padStart(3, "0")}{" "}
                <span style={{ color: NODE_COLOR[activeStep.type] }}>{activeStep.type}</span>
              </div>
            </div>
            <div className="md:col-span-2">
              <div className="text-text-mute uppercase tracking-widest text-[10px]">label</div>
              <div className="text-text-hi truncate mt-0.5">{activeStep.label}</div>
            </div>
            <div>
              <div className="text-text-mute uppercase tracking-widest text-[10px]">latency</div>
              <div className="text-text-hi mt-0.5">
                {activeStep.step.latency_ms !== null
                  ? `${activeStep.step.latency_ms.toFixed(2)} ms`
                  : "—"}
              </div>
            </div>
          </motion.div>
        ) : (
          <div className="text-text-mute flex items-center gap-3 flex-wrap">
            <span>hover a node ·</span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full" style={{ background: NODE_COLOR.model_call }} />
              model
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full" style={{ background: NODE_COLOR.tool_call }} />
              tool
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full" style={{ background: NODE_COLOR.decision }} />
              decision
            </span>
            {failureIndex !== undefined && failureIndex !== null && (
              <span className="text-signal-failure flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-signal-failure" />
                divergence
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
