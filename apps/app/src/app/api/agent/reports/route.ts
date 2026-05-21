import { NextRequest, NextResponse } from "next/server";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import type { ActivityItem } from "@/components/home/RecentActivityFeed";
import type { RecommendedItem } from "@/components/home/RecommendedMetros";
import type { StatCard } from "@/components/home/StatCardRow";
import type { TableRow } from "@/components/reports/ReportsTable";
import { deriveArchetype } from "@/lib/niche-finder/derive-archetype";
import { mapReportRow } from "@/lib/niche-finder/reports-mapper";
import {
  EntitlementError,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";

interface ReportRow {
  id: string;
  niche_keyword: string;
  geo_target: string;
  created_at: string;
  spec_version: string;
  metros: unknown;
  access_scope?: string | null;
  owner_account_id?: string | null;
}

interface MetroScoreV2Row {
  report_id: string;
  spec_version: string | null;
}

function archetypeShort(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.short ?? "Mixed";
}

function isMissingArchivedAtColumn(message: string | undefined): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  return (
    normalized.includes("archived_at") &&
    (normalized.includes("does not exist") || normalized.includes("not found"))
  );
}

function reportsLimit(req: NextRequest) {
  const raw = Number(req.nextUrl.searchParams.get("limit") ?? 50);
  if (!Number.isFinite(raw) || raw <= 0) return 50;
  return Math.min(Math.trunc(raw), 50);
}

function visibleReports(rows: ReportRow[], accountId: string): ReportRow[] {
  return rows.filter(
    (row) => row.access_scope === "cached" || row.owner_account_id === accountId,
  );
}

function toMappedRow(raw: ReportRow, v2ByReportId: Map<string, MetroScoreV2Row>) {
  const mapped = mapReportRow(raw);
  const v2 = v2ByReportId.get(raw.id);
  if (!v2) return mapped;
  return {
    ...mapped,
    spec_version: "2.0",
    opportunity_score: null,
  };
}

function toTableRow(raw: ReportRow, v2ByReportId: Map<string, MetroScoreV2Row>): TableRow {
  const mapped = toMappedRow(raw, v2ByReportId);
  const archetype_id = deriveArchetype({
    opportunity_score: mapped.opportunity_score,
  });
  return {
    id: mapped.id,
    niche: mapped.niche_keyword,
    city: mapped.geo_target,
    archetype_id,
    archetype_short: archetypeShort(archetype_id),
    opportunity_score: mapped.opportunity_score,
    spec_version: mapped.spec_version,
    created_at: mapped.created_at,
  };
}

function toDashboard(rows: ReportRow[], v2ByReportId: Map<string, MetroScoreV2Row>) {
  const scored = rows.map((row) => toMappedRow(row, v2ByReportId));
  const scoresOnly = scored
    .map((row) => row.opportunity_score)
    .filter((score): score is number => typeof score === "number");

  const avg = scoresOnly.length
    ? Math.round(scoresOnly.reduce((a, b) => a + b, 0) / scoresOnly.length)
    : 0;

  const recent: ActivityItem[] = scored.slice(0, 10).map((row) => ({
    id: row.id,
    niche: row.niche_keyword,
    city: row.geo_target,
    created_at: row.created_at,
  }));

  const recommended: RecommendedItem[] = scored.slice(0, 6).map((row) => ({
    id: row.id,
    niche: row.niche_keyword,
    city: row.geo_target,
    score: row.opportunity_score,
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

export async function GET(req: NextRequest) {
  const supabase = await createClient();
  const limit = reportsLimit(req);
  let entitlement;

  try {
    ({ entitlement } = await resolveEntitlementContext(supabase));
  } catch (error) {
    if (error instanceof EntitlementError) {
      return NextResponse.json(
        {
          status: "auth_error",
          code: error.code,
          message: error.message,
        },
        { status: error.status },
      );
    }
    throw error;
  }

  let { data, error } = await supabase
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros, access_scope, owner_account_id")
    .or(`access_scope.eq.cached,owner_account_id.eq.${entitlement.account_id}`)
    .is("archived_at", null)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (isMissingArchivedAtColumn(error?.message)) {
    ({ data, error } = await supabase
      .from("reports")
      .select("id, niche_keyword, geo_target, created_at, spec_version, metros, access_scope, owner_account_id")
      .or(`access_scope.eq.cached,owner_account_id.eq.${entitlement.account_id}`)
      .order("created_at", { ascending: false })
      .limit(limit));
  }

  if (error) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: `reports list: ${error.message}`,
      },
      { status: 502 },
    );
  }

  const rows = visibleReports((data ?? []) as ReportRow[], entitlement.account_id);
  const reportIds = rows.map((row) => row.id);
  const v2ByReportId = new Map<string, MetroScoreV2Row>();
  if (reportIds.length > 0) {
    const { data: v2Data, error: v2Error } = await supabase
      .from("metro_score_v2")
      .select("report_id, spec_version")
      .in("report_id", reportIds);

    if (v2Error) {
      return NextResponse.json(
        {
          status: "unavailable",
          message: `metro_score_v2 list: ${v2Error.message}`,
        },
        { status: 502 },
      );
    }

    for (const row of (v2Data ?? []) as MetroScoreV2Row[]) {
      if (!v2ByReportId.has(row.report_id)) {
        v2ByReportId.set(row.report_id, row);
      }
    }
  }

  return NextResponse.json({
    status: "success",
    reports: rows.map((row) => toTableRow(row, v2ByReportId)),
    dashboard: toDashboard(rows, v2ByReportId),
  });
}
