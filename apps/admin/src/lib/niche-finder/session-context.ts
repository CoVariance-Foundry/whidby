import type { NicheQueryInput } from "@/lib/niche-finder/types";

const STORAGE_KEY = "widby:niche-query-context";

export function saveQueryContext(query: NicheQueryInput): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(query));
}

export function loadQueryContext(): NicheQueryInput | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<NicheQueryInput>;
    if (!parsed.city || !parsed.service) return null;
    // state is optional — previously-stored entries without it are valid.
    return {
      city: parsed.city,
      service: parsed.service,
      ...(typeof parsed.state === "string" && parsed.state ? { state: parsed.state } : {}),
    };
  } catch {
    return null;
  }
}
