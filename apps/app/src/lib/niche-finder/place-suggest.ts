// Mirror of apps/admin/src/lib/niche-finder/place-suggest.ts. Keep in sync until lifted to packages/.

import { fetchMetroSuggestions } from "@/lib/niche-finder/metro-suggest";
import { trackEvent } from "@/lib/analytics/track";

/** Shape returned by /api/agent/places/suggest. */
export interface PlaceSuggestion {
  place_id?: string;
  city: string;
  region?: string | null;
  country: string;
  dataforseo_location_code?: number | null;
  dataforseo_match_confidence?: string | null;
  enrichment_status?:
    | "enriched"
    | "mapbox_only"
    | "not_configured"
    | "timeout"
    | "degraded"
    | "fallback_cbsa";
  enrichment_reason?: string | null;
}

function toFallbackPlaceSuggestions(
  metros: Awaited<ReturnType<typeof fetchMetroSuggestions>>,
): PlaceSuggestion[] {
  return metros.map((metro) => ({
    city: metro.city,
    region: metro.state,
    country: "US",
    enrichment_status: "fallback_cbsa",
    enrichment_reason: "Places API unavailable; used CBSA seed fallback.",
  }));
}

export function formatPlaceSuggestion(suggestion: PlaceSuggestion): string {
  const region = suggestion.region?.trim();
  return region
    ? `${suggestion.city}, ${region}`
    : `${suggestion.city}, ${suggestion.country}`;
}

/**
 * Fetch place suggestions from the consumer proxy.
 * Falls back to the legacy metros proxy if places are unavailable.
 */
export async function fetchPlaceSuggestions(
  query: string,
  limit = 8,
  signal?: AbortSignal,
): Promise<PlaceSuggestion[]> {
  if (!query.trim()) return [];

  const params = new URLSearchParams({ q: query.trim(), limit: String(limit) });

  try {
    const placeRes = await fetch(`/api/agent/places/suggest?${params.toString()}`, {
      signal,
    });

    if (!placeRes.ok) {
      throw new Error(`Place suggest failed: ${placeRes.status}`);
    }

    const places = await placeRes.json() as PlaceSuggestion[];
    return places.map((place) => ({
      ...place,
      enrichment_status: place.enrichment_status ?? "mapbox_only",
    }));
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    trackEvent("autocomplete_fallback_used", {
      fallback_path: "fallback_cbsa",
      reason: error instanceof Error ? error.message : String(error),
    });
    const metros = await fetchMetroSuggestions(query, limit, signal);
    return toFallbackPlaceSuggestions(metros);
  }
}
