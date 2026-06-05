import type { ReportSummary } from "@/lib/api";

/**
 * Tiny SVG sparkline of a single metric across N reports.
 * Designed for the CI dashboard trend cards — bible §8.3 screen 5.
 */
export function Sparkline({
  reports,
  metric,
  width = 220,
  height = 48,
  color = "var(--signal-nominal)",
}: {
  reports: ReportSummary[];
  metric: string;
  width?: number;
  height?: number;
  color?: string;
}) {
  if (reports.length < 2) {
    return (
      <div
        className="font-mono text-[10px] uppercase tracking-widest text-text-mute flex items-center"
        style={{ width, height }}
      >
        not enough runs
      </div>
    );
  }

  const values = reports.map((r) => Math.max(0, Math.min(1, r.aggregate?.[metric] ?? 0)));
  const stepX = width / (values.length - 1);
  const points = values
    .map((v, i) => `${(i * stepX).toFixed(1)},${(height - v * height).toFixed(1)}`)
    .join(" ");

  // Area path under the line.
  const area = `M 0,${height} L ${points} L ${width},${height} Z`;

  // Threshold guide at 0.9 (ship floor).
  const guideY = height - 0.9 * height;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={`trend of ${metric}`}>
      <defs>
        <linearGradient id={`spark-${metric}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <line
        x1={0}
        x2={width}
        y1={guideY}
        y2={guideY}
        stroke="rgba(255,255,255,0.08)"
        strokeDasharray="3 4"
      />
      <path d={area} fill={`url(#spark-${metric})`} />
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />
      {values.map((v, i) => {
        const x = i * stepX;
        const y = height - v * height;
        const cellColor = v >= 0.9 ? "var(--signal-nominal)" : v >= 0.6 ? "var(--signal-warning)" : "var(--signal-failure)";
        return <circle key={i} cx={x} cy={y} r={2.2} fill={cellColor} />;
      })}
    </svg>
  );
}
