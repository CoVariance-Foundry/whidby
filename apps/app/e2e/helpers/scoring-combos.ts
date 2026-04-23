/**
 * Shared city/service combinations for the scoring E2E matrix.
 *
 * Tier 1: well-known metros already in the CBSA seed — baseline reliability.
 * Tier 2: smaller / edge-case metros that stress metro resolution, provider
 *         coverage, and niche-keyword diversity.
 */

export interface ScoringCombo {
  city: string;
  service: string;
  /** Two-letter state code (optional — helps disambiguate). */
  state?: string;
  /** DataForSEO location code if testing the canonical-place path. */
  dataforseo_location_code?: number;
  tier: 1 | 2;
  /** Short tag for logs and artifact filenames. */
  tag: string;
}

export const TIER_1_COMBOS: ScoringCombo[] = [
  { city: "Phoenix",       service: "roofing",                     state: "AZ", tier: 1, tag: "phoenix-roofing" },
  { city: "Chicago",       service: "paving",                      state: "IL", tier: 1, tag: "chicago-paving" },
  { city: "Tampa",         service: "water damage restoration",    state: "FL", tier: 1, tag: "tampa-wdr" },
  { city: "Indianapolis",  service: "snow removal",                state: "IN", tier: 1, tag: "indianapolis-snow" },
  { city: "Dallas",        service: "HVAC repair",                 state: "TX", tier: 1, tag: "dallas-hvac" },
];

export const TIER_2_COMBOS: ScoringCombo[] = [
  { city: "Huntsville",    service: "tree removal",                state: "AL", tier: 2, tag: "huntsville-tree" },
  { city: "Boise",         service: "epoxy flooring",              state: "ID", tier: 2, tag: "boise-epoxy" },
  { city: "Albuquerque",   service: "junk removal",                state: "NM", tier: 2, tag: "albuquerque-junk" },
  { city: "Spokane",       service: "pest control",                state: "WA", tier: 2, tag: "spokane-pest" },
  { city: "Savannah",      service: "mold remediation",            state: "GA", tier: 2, tag: "savannah-mold" },
];

export const ALL_COMBOS: ScoringCombo[] = [...TIER_1_COMBOS, ...TIER_2_COMBOS];

/**
 * Build the POST body for the scoring proxy from a combo definition.
 */
export function comboToRequestBody(combo: ScoringCombo): Record<string, unknown> {
  const body: Record<string, unknown> = {
    city: combo.city,
    service: combo.service,
  };
  if (combo.state) body.state = combo.state;
  if (typeof combo.dataforseo_location_code === "number") {
    body.dataforseo_location_code = combo.dataforseo_location_code;
  }
  return body;
}

/**
 * Shape of each per-run metric record emitted as a test attachment.
 */
export interface RunMetric {
  combo: string;
  tier: 1 | 2;
  runIndex: number;
  status: "pass" | "fail" | "error";
  httpStatus: number;
  reportId: string | null;
  opportunityScore: number | null;
  latencyMs: number;
  upstreamStatus: number | null;
  errorMessage: string | null;
  timestamp: string;
}
