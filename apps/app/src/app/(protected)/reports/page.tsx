import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Icon, I } from "@/lib/icons";
import { createClient } from "@/lib/supabase/server";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { mapReportRow } from "@/lib/niche-finder/reports-mapper";
import { deriveArchetype } from "@/lib/niche-finder/derive-archetype";
import type { TableRow } from "@/components/reports/ReportsTable";
import ReportsPageClient from "./ReportsPageClient";

export const dynamic = "force-dynamic";

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

export default async function ReportsPage() {
  const supabase = await createClient();
  let { data, error } = await supabase
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
    .is("archived_at", null)
    .order("created_at", { ascending: false })
    .limit(50);

  // Some environments can lag the migration that adds `reports.archived_at`.
  // If that column is missing, retry the list query without the filter.
  if (isMissingArchivedAtColumn(error?.message)) {
    ({ data, error } = await supabase
      .from("reports")
      .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
      .order("created_at", { ascending: false })
      .limit(50));
  }

  if (error) {
    throw new Error(`reports list: ${error.message}`);
  }

  const rows: TableRow[] = (data ?? []).map((raw) => {
    const m = mapReportRow(raw);
    const archetype_id = deriveArchetype({
      opportunity_score: m.opportunity_score,
    });
    return {
      id: m.id,
      niche: m.niche_keyword,
      city: m.geo_target,
      archetype_id,
      archetype_short: archetypeShort(archetype_id),
      opportunity_score: m.opportunity_score,
      spec_version: m.spec_version,
      created_at: m.created_at,
    };
  });

  return (
    <div className="app density-roomy">
      <Sidebar active="reports" />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar
          crumbs={["Reports"]}
          actions={
            <Link href="/niche-finder" className="btn-primary" style={{ textDecoration: "none", display: "inline-flex" }}>
              <Icon d={I.plus} /> New report
            </Link>
          }
        />
        <main
          style={{
            padding: "24px 32px",
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <header>
            <h1
              style={{
                fontFamily: "var(--serif)",
                fontSize: 28,
                fontWeight: 600,
                color: "var(--ink)",
                margin: 0,
              }}
            >
              Reports
            </h1>
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "4px 0 0",
              }}
            >
              Every niche score you've run, most recent first.
            </p>
          </header>
          <ReportsPageClient rows={rows} />
        </main>
      </div>
    </div>
  );
}
