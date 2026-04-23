import { describe, it, expect, beforeEach } from "vitest";
import {
  loadRecent,
  pushRecent,
  loadPinned,
  togglePinned,
  type HistoryEntry,
} from "./history-storage";

const memStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (k: string) => memStore[k] ?? null,
  setItem: (k: string, v: string) => { memStore[k] = v; },
  removeItem: (k: string) => { delete memStore[k]; },
  clear: () => { for (const k of Object.keys(memStore)) delete memStore[k]; },
  get length() { return Object.keys(memStore).length; },
  key: (i: number) => Object.keys(memStore)[i] ?? null,
};

beforeEach(() => {
  mockLocalStorage.clear();
  Object.defineProperty(globalThis, "localStorage", {
    value: mockLocalStorage,
    configurable: true,
  });
});

describe("history-storage", () => {
  it("pushRecent prepends to recent and caps at 8 entries", () => {
    for (let i = 0; i < 10; i++) {
      pushRecent({ city: `City ${i}`, service: `svc-${i}`, at: i });
    }
    const recent = loadRecent();
    expect(recent.length).toBe(8);
    expect(recent[0].at).toBe(9);
  });

  it("togglePinned adds then removes an entry", () => {
    const entry: HistoryEntry = { city: "Austin, TX", service: "plumber", at: 1 };
    togglePinned(entry);
    expect(loadPinned()).toHaveLength(1);
    togglePinned(entry);
    expect(loadPinned()).toHaveLength(0);
  });

  it("returns empty arrays when storage is blank", () => {
    expect(loadRecent()).toEqual([]);
    expect(loadPinned()).toEqual([]);
  });

  it("preserves optional place targeting metadata", () => {
    pushRecent({
      city: "Phoenix",
      service: "roofing",
      state: "AZ",
      place_id: "place.phoenix",
      dataforseo_location_code: 1012873,
      at: 42,
    });
    const [recent] = loadRecent();
    expect(recent.state).toBe("AZ");
    expect(recent.place_id).toBe("place.phoenix");
    expect(recent.dataforseo_location_code).toBe(1012873);
  });

  it("keeps distinct recents when place_id differs for same city/service", () => {
    pushRecent({
      city: "Springfield",
      service: "roofing",
      state: "IL",
      place_id: "place.springfield-il",
      dataforseo_location_code: 111,
      at: 1,
    });
    pushRecent({
      city: "Springfield",
      service: "roofing",
      state: "MO",
      place_id: "place.springfield-mo",
      dataforseo_location_code: 222,
      at: 2,
    });

    const recent = loadRecent();
    expect(recent).toHaveLength(2);
    expect(recent[0].place_id).toBe("place.springfield-mo");
    expect(recent[1].place_id).toBe("place.springfield-il");
  });
});
