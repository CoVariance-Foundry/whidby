export interface HistoryEntry {
  city: string;
  service: string;
  at: number;
  state?: string;
  place_id?: string;
  dataforseo_location_code?: number;
}

const RECENT_KEY = "widby.niche.recent";
const PINNED_KEY = "widby.niche.pinned";
const RECENT_CAP = 8;

function safeParse(raw: string | null): HistoryEntry[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is HistoryEntry =>
        typeof x === "object" && x !== null &&
        typeof (x as HistoryEntry).city === "string" &&
        typeof (x as HistoryEntry).service === "string" &&
        typeof (x as HistoryEntry).at === "number" &&
        ((x as HistoryEntry).state === undefined || typeof (x as HistoryEntry).state === "string") &&
        ((x as HistoryEntry).place_id === undefined || typeof (x as HistoryEntry).place_id === "string") &&
        (
          (x as HistoryEntry).dataforseo_location_code === undefined ||
          typeof (x as HistoryEntry).dataforseo_location_code === "number"
        ),
    );
  } catch { return []; }
}

function key(entry: HistoryEntry): string {
  const service = entry.service.trim().toLowerCase();
  const placeId = entry.place_id?.trim().toLowerCase();
  if (placeId) {
    return `place:${placeId}|service:${service}`;
  }
  const city = entry.city.trim().toLowerCase();
  const state = entry.state?.trim().toLowerCase() ?? "";
  const dfsCode =
    typeof entry.dataforseo_location_code === "number"
      ? String(entry.dataforseo_location_code)
      : "";
  return `city:${city}|state:${state}|dfs:${dfsCode}|service:${service}`;
}

export function loadRecent(): HistoryEntry[] {
  if (typeof localStorage === "undefined") return [];
  return safeParse(localStorage.getItem(RECENT_KEY));
}

export function pushRecent(entry: HistoryEntry): void {
  if (typeof localStorage === "undefined") return;
  const existing = loadRecent().filter((e) => key(e) !== key(entry));
  const next = [entry, ...existing].slice(0, RECENT_CAP);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function loadPinned(): HistoryEntry[] {
  if (typeof localStorage === "undefined") return [];
  return safeParse(localStorage.getItem(PINNED_KEY));
}

export function togglePinned(entry: HistoryEntry): void {
  if (typeof localStorage === "undefined") return;
  const existing = loadPinned();
  const k = key(entry);
  const found = existing.find((e) => key(e) === k);
  const next = found
    ? existing.filter((e) => key(e) !== k)
    : [entry, ...existing];
  localStorage.setItem(PINNED_KEY, JSON.stringify(next));
}
