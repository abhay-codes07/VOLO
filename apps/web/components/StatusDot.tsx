export function StatusDot({
  status,
  label,
}: {
  status: "nominal" | "warning" | "failure" | "info" | "muted";
  label?: string;
}) {
  const color: Record<typeof status, string> = {
    nominal: "bg-signal-nominal",
    warning: "bg-signal-warning",
    failure: "bg-signal-failure",
    info: "bg-signal-info",
    muted: "bg-text-mute",
  };
  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-text-lo">
      <span className={`inline-block h-2 w-2 rounded-full ${color[status]}`} aria-hidden />
      {label}
    </span>
  );
}
