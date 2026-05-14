import type { SupabaseClient } from "@supabase/supabase-js";

export interface ExploreScoreTrendRow {
  scored_at: string;
  opportunity_score: number | null;
  opportunity_delta: number | null;
}

interface ExploreScoreTrendSourceRow {
  scored_at: string | null;
  opportunity_score: number | string | null;
  opportunity_delta: number | string | null;
}

function asNumber(value: number | string | null | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function hasValidScoredAt(
  row: ExploreScoreTrendSourceRow
): row is ExploreScoreTrendSourceRow & { scored_at: string } {
  return Boolean(row.scored_at && Number.isFinite(Date.parse(row.scored_at)));
}

export async function loadScoreTrends(
  client: SupabaseClient,
  refreshTargetId: string
): Promise<ExploreScoreTrendRow[]> {
  const { data, error } = await client
    .from("explore_target_trends")
    .select("scored_at, opportunity_score, opportunity_delta")
    .eq("target_id", refreshTargetId)
    .order("scored_at", { ascending: true })
    .limit(24);

  if (error) {
    throw new Error(`loadScoreTrends explore_target_trends: ${error.message}`);
  }

  return ((data ?? []) as ExploreScoreTrendSourceRow[])
    .filter(hasValidScoredAt)
    .map((row) => ({
      scored_at: row.scored_at,
      opportunity_score: asNumber(row.opportunity_score),
      opportunity_delta: asNumber(row.opportunity_delta),
    }));
}
