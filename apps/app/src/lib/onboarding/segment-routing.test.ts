import { describe, expect, it } from "vitest";
import {
  isOnboardingNextRoute,
  resolveOnboardingSegmentRoute,
  routeForOnboardingIntent,
} from "./segment-routing";

// @req FR-101
describe("resolveOnboardingSegmentRoute", () => {
  it.each([
    ["find_first", "/"],
    ["scale", "/strategies"],
    ["coach_agency", "/agency"],
    ["researching", "/explore"],
  ] as const)("routes %s intent to %s", (intent, route) => {
    expect(routeForOnboardingIntent(intent)).toBe(route);
    expect(resolveOnboardingSegmentRoute({ profile: { intent } })).toEqual({
      segment: intent,
      route,
      source: "intent",
    });
  });

  it("lets persisted intent override stale stored routes", () => {
    expect(
      resolveOnboardingSegmentRoute({
        profile: {
          intent: "find_first",
          next_route: "/strategies",
        },
        report_history: { completed_report_count: 3 },
      }),
    ).toEqual({
      segment: "find_first",
      route: "/",
      source: "intent",
    });
  });

  it("upgrades profiles without intent from existing report history", () => {
    expect(
      resolveOnboardingSegmentRoute({
        profile: { next_route: "/" },
        report_history: { completed_report_count: 1 },
      }),
    ).toEqual({
      segment: "scale",
      route: "/strategies",
      source: "report_history",
    });
  });

  it("falls back to a safe stored route when intent and history are absent", () => {
    expect(
      resolveOnboardingSegmentRoute({
        profile: { next_route: "/explore" },
      }),
    ).toEqual({
      segment: "researching",
      route: "/explore",
      source: "stored_route",
    });
  });

  it("defaults unknown or unsafe routes to the dashboard", () => {
    expect(isOnboardingNextRoute("https://example.test/not-allowed")).toBe(false);
    expect(
      resolveOnboardingSegmentRoute({
        profile: { intent: "unknown", next_route: "https://example.test/not-allowed" },
      }),
    ).toEqual({
      segment: "find_first",
      route: "/",
      source: "default",
    });
  });
});
