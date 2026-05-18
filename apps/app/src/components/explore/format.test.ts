import { describe, expect, it } from "vitest";
import { formatPercent } from "./format";

describe("formatPercent", () => {
  it("formats canonical decimal growth as a percent", () => {
    expect(formatPercent(0.032)).toBe("3.2%");
    expect(formatPercent(null)).toBe("-");
  });
});
