// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AIResilienceFlagBadge } from "./AIResilienceFlagBadge";

afterEach(() => {
  cleanup();
});

describe("AIResilienceFlagBadge", () => {
  it("announces flagged fractional scores without rounding up to the threshold", () => {
    render(<AIResilienceFlagBadge score={39.7} threshold={40} />);

    expect(
      screen.getByRole("img", {
        name: "AI Resilience flagged: score 39 below threshold 40",
      }),
    ).toBeInTheDocument();
  });

  it("does not render when the score meets the threshold", () => {
    render(<AIResilienceFlagBadge score={40} threshold={40} />);

    expect(screen.queryByText("AI resilience flagged")).not.toBeInTheDocument();
  });
});
