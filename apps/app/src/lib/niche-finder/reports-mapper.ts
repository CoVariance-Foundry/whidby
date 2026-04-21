export interface ReportListRow {
  id: string;
  niche_keyword: string;
  geo_target: string;
  created_at: string;
  spec_version: string;
  opportunity_score: number | null;
}

export function mapReportRow(row: {
  id: string;
  niche_keyword: string;
  geo_target: string;
  created_at: string;
  spec_version: string;
  metros: unknown;
}): ReportListRow {
  let opportunity_score: number | null = null;
  if (Array.isArray(row.metros) && row.metros.length > 0) {
    const scores = (row.metros[0] as { scores?: { opportunity?: number } })?.scores;
    if (typeof scores?.opportunity === "number") {
      opportunity_score = Math.round(scores.opportunity);
    }
  }
  return {
    id: row.id,
    niche_keyword: row.niche_keyword,
    geo_target: row.geo_target,
    created_at: row.created_at,
    spec_version: row.spec_version,
    opportunity_score,
  };
}
