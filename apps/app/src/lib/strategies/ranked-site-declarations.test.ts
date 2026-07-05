import { describe, expect, it } from "vitest";
import {
  isRankedSiteDeclarationUnlocking,
  normalizeRankedSiteDomain,
  normalizeRankedSiteNiche,
  summarizeRankedSiteUnlock,
  type RankedSiteDeclaration,
} from "./ranked-site-declarations";

// @req FR-104
describe("ranked-site declaration helpers", () => {
  it("normalizes domains from URLs and direct hostnames", () => {
    expect(normalizeRankedSiteDomain("https://www.Example.com/path?q=1")).toBe(
      "example.com",
    );
    expect(normalizeRankedSiteDomain("subdomain.example.co.uk/services")).toBe(
      "subdomain.example.co.uk",
    );
    expect(normalizeRankedSiteDomain("example")).toBeNull();
    expect(normalizeRankedSiteDomain("not a domain")).toBeNull();
  });

  it("normalizes niche labels into stable keys", () => {
    expect(normalizeRankedSiteNiche("Water Damage & Mold Repair")).toBe(
      "water_damage_and_mold_repair",
    );
    expect(normalizeRankedSiteNiche("  Roofing Contractor  ")).toBe(
      "roofing_contractor",
    );
  });

  it("unlocks Expand & Conquer only for active declared or verified rows", () => {
    expect(
      isRankedSiteDeclarationUnlocking({ active: true, proof_state: "declared" }),
    ).toBe(true);
    expect(
      isRankedSiteDeclarationUnlocking({ active: true, proof_state: "verified" }),
    ).toBe(true);
    expect(
      isRankedSiteDeclarationUnlocking({ active: true, proof_state: "needs_review" }),
    ).toBe(false);
    expect(
      isRankedSiteDeclarationUnlocking({ active: false, proof_state: "declared" }),
    ).toBe(false);
  });

  it("summarizes the active unlock declaration for route consumers", () => {
    const declarations: RankedSiteDeclaration[] = [
      declaration({ id: "inactive", active: false, proof_state: "declared" }),
      declaration({ id: "pending", active: true, proof_state: "needs_review" }),
      declaration({ id: "winner", active: true, proof_state: "verified" }),
    ];

    expect(summarizeRankedSiteUnlock(declarations)).toMatchObject({
      requirement_id: "ranked_site_declaration",
      expand_conquer_unlocked: true,
      unlocked_strategy_ids: ["expand_conquer"],
      active_declaration_id: "winner",
      active_declaration: { id: "winner" },
    });
  });
});

function declaration(
  overrides: Partial<RankedSiteDeclaration>,
): RankedSiteDeclaration {
  return {
    id: "declaration-1",
    site_name: "Phoenix Roofing",
    site_url: "https://phoenix-roofing.example",
    site_domain: "phoenix-roofing.example",
    city: "Phoenix",
    state: "AZ",
    cbsa_code: null,
    niche_keyword: "roofing",
    niche_normalized: "roofing",
    proof_state: "declared",
    active: true,
    metadata: {},
    ...overrides,
  };
}
