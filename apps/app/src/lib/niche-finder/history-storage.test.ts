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
});
