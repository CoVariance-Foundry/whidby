/** Shape returned by /api/agent/metros/suggest (mirrors FastAPI MetroSuggest schema). */
export interface MetroSuggestion {
  cbsa_code: string;
  city: string;
  state: string;
  cbsa_name: string;
  population: number;
}

/**
 * Fetch metro suggestions from the admin proxy.
 *
 * @param query   Partial city string (≥ 1 char)
 * @param limit   Max results (default: 8)
 * @param signal  Optional AbortSignal for in-flight cancellation
 */
export async function fetchMetroSuggestions(
  query: string,
  limit = 8,
  signal?: AbortSignal,
): Promise<MetroSuggestion[]> {
  if (!query.trim()) return [];

  const params = new URLSearchParams({ q: query.trim(), limit: String(limit) });
  const res = await fetch(`/api/agent/metros/suggest?${params.toString()}`, {
    signal,
  });

  if (!res.ok) {
    throw new Error(`Metro suggest failed: ${res.status}`);
  }

  return res.json() as Promise<MetroSuggestion[]>;
}
