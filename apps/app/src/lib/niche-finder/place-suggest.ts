// Mirror of apps/admin/src/lib/niche-finder/place-suggest.ts. Keep in sync until lifted to packages/.

import { fetchMetroSuggestions } from "@/lib/niche-finder/metro-suggest";

/** Shape returned by /api/agent/places/suggest. */
export interface PlaceSuggestion {
  place_id?: string;
  city: string;
  region?: string | null;
  country: string;
  dataforseo_location_code?: number | null;
  dataforseo_match_confidence?: string | null;
}

function toFallbackPlaceSuggestions(
  metros: Awaited<ReturnType<typeof fetchMetroSuggestions>>,
): PlaceSuggestion[] {
  return metros.map((metro) => ({
    city: metro.city,
    region: metro.state,
    country: "US",
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

    return await placeRes.json() as PlaceSuggestion[];
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    const metros = await fetchMetroSuggestions(query, limit, signal);
    return toFallbackPlaceSuggestions(metros);
  }
}
