const API_BASE = process.env.NEXT_PUBLIC_VOLO_API ?? "http://localhost:8080";

export type ShadowCheck = {
  at: string | null;
  aggregate: Record<string, number>;
  drifted: boolean;
  findings: number;
  traces: number;
};

export type CorpusTrace = {
  run_id: string;
  source: string;
  agent_name: string | null;
  steps: number;
  added_at: string;
};

export type ShadowHistory = {
  checks: ShadowCheck[];
  corpus: CorpusTrace[];
};

export async function getShadowHistory(): Promise<ShadowHistory> {
  const res = await fetch(`${API_BASE}/shadow/history`, { cache: "no-store" });
  if (!res.ok) throw new Error(`/shadow/history -> ${res.status}`);
  return (await res.json()) as ShadowHistory;
}
