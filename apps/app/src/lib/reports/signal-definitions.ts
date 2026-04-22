export type SignalFormat = "number" | "percent" | "currency" | "boolean" | "count";
export type SignalDirection = "higher_better" | "lower_better";

export interface SignalDefinition {
  label: string;
  format: SignalFormat;
  direction: SignalDirection;
  description: string;
}

export type SignalCategory =
  | "demand"
  | "organic_competition"
  | "local_competition"
  | "monetization"
  | "ai_resilience";

export const SIGNAL_DEFINITIONS: Record<SignalCategory, Record<string, SignalDefinition>> = {
  demand: {
    total_search_volume: {
      label: "Total search volume",
      format: "count",
      direction: "higher_better",
      description: "Combined monthly searches across all keywords in this niche.",
    },
    effective_search_volume: {
      label: "Effective search volume",
      format: "count",
      direction: "higher_better",
      description: "Volume adjusted for intent quality and AI Overview cannibalization.",
    },
    head_term_volume: {
      label: "Head term volume",
      format: "count",
      direction: "higher_better",
      description: "Monthly searches for the primary tier-1 keyword alone.",
    },
    volume_breadth: {
      label: "Volume breadth",
      format: "percent",
      direction: "higher_better",
      description: "Proportion of keywords with non-zero search volume.",
    },
    avg_cpc: {
      label: "Avg. CPC",
      format: "currency",
      direction: "higher_better",
      description: "Volume-weighted average cost-per-click, a proxy for lead value.",
    },
    max_cpc: {
      label: "Max CPC (tier 1-2)",
      format: "currency",
      direction: "higher_better",
      description: "Highest CPC among tier-1 and tier-2 keywords.",
    },
    cpc_volume_product: {
      label: "CPC x Volume",
      format: "number",
      direction: "higher_better",
      description: "Effective volume multiplied by avg. CPC -- total addressable value.",
    },
    transactional_ratio: {
      label: "Transactional ratio",
      format: "percent",
      direction: "higher_better",
      description: "Share of search volume from transactional (buyer-intent) keywords.",
    },
  },

  organic_competition: {
    avg_top5_da: {
      label: "Avg. DA (top 5)",
      format: "number",
      direction: "lower_better",
      description: "Average domain authority of the top 5 organic results.",
    },
    min_top5_da: {
      label: "Min DA (top 5)",
      format: "number",
      direction: "lower_better",
      description: "Lowest domain authority in the top 5 -- your entry point.",
    },
    da_spread: {
      label: "DA spread",
      format: "number",
      direction: "higher_better",
      description: "Gap between strongest and weakest top-5 competitor. High spread = uneven field.",
    },
    aggregator_count: {
      label: "Aggregators",
      format: "count",
      direction: "lower_better",
      description: "Number of lead-gen aggregators (Yelp, Angi, etc.) in organic results.",
    },
    local_biz_count: {
      label: "Local businesses",
      format: "count",
      direction: "higher_better",
      description: "Number of small local businesses ranking organically -- beatable competitors.",
    },
    avg_lighthouse_performance: {
      label: "Avg. Lighthouse score",
      format: "number",
      direction: "lower_better",
      description: "Average page speed score of competitors. Low = technically weak.",
    },
    schema_adoption_rate: {
      label: "Schema adoption",
      format: "percent",
      direction: "lower_better",
      description: "Share of competitors using structured data. Low = SEO underinvestment.",
    },
    title_keyword_match_rate: {
      label: "Title keyword match",
      format: "percent",
      direction: "lower_better",
      description: "Share of top results with the keyword in the title. Low = poor targeting.",
    },
  },

  local_competition: {
    local_pack_present: {
      label: "Local Pack shown",
      format: "boolean",
      direction: "higher_better",
      description: "Whether Google shows a Local Pack for this query.",
    },
    local_pack_position: {
      label: "Local Pack position",
      format: "count",
      direction: "lower_better",
      description: "SERP position of the Local Pack (lower = more prominent).",
    },
    local_pack_review_count_avg: {
      label: "Avg. reviews",
      format: "number",
      direction: "lower_better",
      description: "Average review count among Local Pack incumbents.",
    },
    local_pack_review_count_max: {
      label: "Max reviews",
      format: "number",
      direction: "lower_better",
      description: "Highest review count in the Local Pack -- the ceiling you must beat.",
    },
    local_pack_rating_avg: {
      label: "Avg. rating",
      format: "number",
      direction: "lower_better",
      description: "Average star rating in the Local Pack.",
    },
    review_velocity_avg: {
      label: "Review velocity",
      format: "number",
      direction: "lower_better",
      description: "Average new reviews per month among incumbents. Low = stagnant.",
    },
    gbp_completeness_avg: {
      label: "GBP completeness",
      format: "percent",
      direction: "lower_better",
      description: "How complete incumbent Google Business Profiles are. Low = under-optimized.",
    },
    gbp_photo_count_avg: {
      label: "Avg. GBP photos",
      format: "number",
      direction: "lower_better",
      description: "Average photo count on competitor profiles. Low = less investment.",
    },
    gbp_posting_activity: {
      label: "GBP posting activity",
      format: "percent",
      direction: "lower_better",
      description: "Share of competitors with recent GBP posts. Low = inactive profiles.",
    },
    citation_consistency: {
      label: "Citation consistency",
      format: "percent",
      direction: "lower_better",
      description: "NAP (name/address/phone) consistency across directories.",
    },
  },

  monetization: {
    avg_cpc: {
      label: "Avg. CPC",
      format: "currency",
      direction: "higher_better",
      description: "Average cost-per-click for this niche, indicating how much businesses pay for leads.",
    },
    business_density: {
      label: "Business density",
      format: "count",
      direction: "higher_better",
      description: "Number of local businesses found -- more = more potential lead buyers.",
    },
    gbp_completeness_avg: {
      label: "GBP completeness",
      format: "percent",
      direction: "higher_better",
      description: "How invested local businesses are in their online presence.",
    },
    lsa_present: {
      label: "Local Services Ads",
      format: "boolean",
      direction: "higher_better",
      description: "Whether Google Local Services Ads appear -- validates paid lead demand.",
    },
    aggregator_presence: {
      label: "Aggregator count",
      format: "count",
      direction: "higher_better",
      description: "Number of lead-gen aggregators -- confirms the lead-selling model works.",
    },
    ads_present: {
      label: "Paid ads present",
      format: "boolean",
      direction: "higher_better",
      description: "Whether businesses are running paid search ads for this niche.",
    },
  },

  ai_resilience: {
    aio_trigger_rate: {
      label: "AI Overview trigger rate",
      format: "percent",
      direction: "lower_better",
      description: "How often Google shows an AI Overview for these keywords. Lower = safer.",
    },
    featured_snippet_rate: {
      label: "Featured snippet rate",
      format: "percent",
      direction: "lower_better",
      description: "How often a featured snippet appears. Snippets can reduce organic clicks.",
    },
    transactional_keyword_ratio: {
      label: "Transactional keyword ratio",
      format: "percent",
      direction: "higher_better",
      description: "Share of keywords with buyer intent -- harder for AI to satisfy.",
    },
    local_fulfillment_required: {
      label: "Requires local fulfillment",
      format: "boolean",
      direction: "higher_better",
      description: "Whether the service requires a physical visit -- AI-proof by nature.",
    },
    paa_density: {
      label: "PAA density",
      format: "number",
      direction: "lower_better",
      description: "Average 'People Also Ask' boxes per query. High = Google sees query as informational.",
    },
  },
};

export function formatSignalValue(value: unknown, format: SignalFormat): string {
  if (value == null) return "--";
  if (format === "boolean") return value ? "Yes" : "No";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  switch (format) {
    case "percent":
      return num <= 1 ? `${(num * 100).toFixed(0)}%` : `${num.toFixed(0)}%`;
    case "currency":
      return `$${num.toFixed(2)}`;
    case "count":
      return num >= 1000 ? num.toLocaleString("en-US", { maximumFractionDigits: 0 }) : String(Math.round(num));
    case "number":
    default:
      return num >= 100 ? num.toLocaleString("en-US", { maximumFractionDigits: 0 }) : num.toFixed(1);
  }
}
