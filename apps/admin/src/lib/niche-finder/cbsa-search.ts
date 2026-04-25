// Mirror of apps/app/src/lib/niche-finder/cbsa-search.ts. Keep in sync until lifted to packages/.
// Port of src/data/metro_db.py search logic for use in the Next.js route handler.

import type { MetroSuggestion } from "./metro-suggest";
import seed from "@/data/cbsa-seed.json";

interface CbsaRow {
  cbsa_code: string;
  cbsa_name: string;
  state: string;
  population: number;
  principal_cities: string[];
}

const rows: CbsaRow[] = seed as CbsaRow[];

export function searchMetros(query: string, limit: number): MetroSuggestion[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];

  const matches: { row: CbsaRow; city: string }[] = [];

  for (const row of rows) {
    const matchedCity = row.principal_cities.find((pc) =>
      pc.toLowerCase().startsWith(q),
    );
    if (matchedCity) {
      matches.push({ row, city: matchedCity });
    } else if (row.cbsa_name.toLowerCase().includes(q)) {
      matches.push({ row, city: row.principal_cities[0] ?? row.cbsa_name });
    }
  }

  matches.sort((a, b) => b.row.population - a.row.population);

  return matches.slice(0, limit).map(({ row, city }) => ({
    cbsa_code: row.cbsa_code,
    city,
    state: row.state,
    cbsa_name: row.cbsa_name,
    population: row.population,
  }));
}
