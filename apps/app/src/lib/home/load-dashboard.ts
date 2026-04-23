import type { SupabaseClient } from "@supabase/supabase-js";
import type { ActivityItem } from "@/components/home/RecentActivityFeed";
import type { RecommendedItem } from "@/components/home/RecommendedMetros";
import type { StatCard } from "@/components/home/StatCardRow";

interface ReportRow {
  id: string;
  niche_keyword: string;
  geo_target: string;
  created_at: string;
  spec_version: string;
  metros: unknown;
}

function extractScore(metros: unknown): number | null {
  if (!Array.isArray(metros) || metros.length === 0) return null;
  const first = metros[0] as { scores?: { opportunity?: number } };
  const raw = first?.scores?.opportunity;
  return typeof raw === "number" ? Math.round(raw) : null;
}

export interface DashboardData {
  stats: {
    total_reports: number;
    avg_score: number;
    watchlist: number; // placeholder: 0 until saved-searches ships
    niches_scored: number; // same as total_reports in Foundation; diverges later
  };
  recent: ActivityItem[];
  recommended: RecommendedItem[];
  stat_cards: StatCard[];
}

export async function loadDashboard(client: SupabaseClient): Promise<DashboardData> {
  const { data, error } = await client
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
    .is("archived_at", null)
    .order("created_at", { ascending: false })
    .limit(10);

  if (error) {
    throw new Error(`loadDashboard: ${error.message}`);
  }

  const rows = (data ?? []) as ReportRow[];
  const scored = rows.map((r) => ({ row: r, score: extractScore(r.metros) }));
  const scoresOnly = scored
    .map((s) => s.score)
    .filter((s): s is number => typeof s === "number");

  const avg = scoresOnly.length
    ? Math.round(scoresOnly.reduce((a, b) => a + b, 0) / scoresOnly.length)
    : 0;

  const recent: ActivityItem[] = scored.slice(0, 10).map((s) => ({
    id: s.row.id,
    niche: s.row.niche_keyword,
    city: s.row.geo_target,
    created_at: s.row.created_at,
  }));

  const recommended: RecommendedItem[] = scored.slice(0, 6).map((s) => ({
    id: s.row.id,
    niche: s.row.niche_keyword,
    city: s.row.geo_target,
    score: s.score,
  }));

  const stats = {
    total_reports: rows.length,
    avg_score: avg,
    watchlist: 0,
    niches_scored: rows.length,
  };

  const stat_cards: StatCard[] = [
    { label: "Niches scored", value: String(stats.niches_scored) },
    { label: "Watchlist", value: String(stats.watchlist) },
    { label: "Avg score", value: String(stats.avg_score) },
    { label: "Reports", value: String(stats.total_reports) },
  ];

  return { stats, recent, recommended, stat_cards };
}
