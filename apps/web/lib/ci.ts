import type { ReportSummary } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_VOLO_API ?? "http://localhost:8080";

export type CIReport = ReportSummary & { created_at?: string };

export async function listCIReports(): Promise<CIReport[]> {
  const res = await fetch(`${API_BASE}/ci/reports`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/ci/reports -> ${res.status}`);
  return (await res.json()) as CIReport[];
}
