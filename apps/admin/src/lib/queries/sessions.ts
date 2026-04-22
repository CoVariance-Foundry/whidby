import { queryKeys } from "@/lib/query-keys";
import type { UseQueryOptions } from "@tanstack/react-query";

export interface Session {
  run_id: string;
  completed?: boolean;
  stop_reason?: string;
  iterations_completed?: number;
  total_cost_usd?: number;
  validated_count?: number;
  invalidated_count?: number;
  saved_at?: string;
}

async function fetchSessions(): Promise<Session[]> {
  const res = await fetch("/api/agent/sessions");
  if (!res.ok) return [];
  return res.json();
}

export function sessionsQueryOptions(): UseQueryOptions<Session[]> {
  return {
    queryKey: queryKeys.sessions.all as unknown as string[],
    queryFn: fetchSessions,
    staleTime: 60_000,
  };
}

export interface SessionDetail {
  run_id: string;
  progress?: Array<{
    experiment_id?: string;
    hypothesis_id?: string;
    validated?: boolean;
    delta?: number;
    baseline_score?: number;
    candidate_score?: number;
    learning?: string;
    cost_usd?: number;
  }>;
}

export async function fetchSessionDetail(runId: string): Promise<SessionDetail> {
  const res = await fetch(`/api/agent/sessions/${runId}`);
  if (!res.ok) throw new Error(`Failed to load session ${runId}`);
  return res.json();
}
