import { createClient } from "@/lib/supabase/server";
import { mapReportRow } from "@/lib/niche-finder/reports-mapper";
import ReportsView from "./ReportsView";

// This page reads from Supabase at request time — never statically prerender.
export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  const supabase = await createClient();

  const { data, error } = await supabase
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) {
    console.error("[ReportsPage] Supabase fetch error:", error.message);
  }

  const rows = (data ?? []).map(mapReportRow);

  return <ReportsView rows={rows} />;
}
