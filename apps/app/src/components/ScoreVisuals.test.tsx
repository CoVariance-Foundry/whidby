// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ScoreBar, ScoreCircle } from "./ScoreVisuals";

afterEach(() => {
  cleanup();
});

describe("ScoreCircle", () => {
  it.each([
    [80, "high"],
    [60, "good"],
    [40, "warning"],
    [39, "danger"],
  ])("labels %i as %s", (value, tone) => {
    render(<ScoreCircle value={value} label="Opportunity" />);

    const circle = screen.getByRole("img", { name: `Opportunity: ${value} out of 100, ${tone}` });
    expect(circle).toHaveAttribute("data-score-tone", tone);
    expect(circle).toHaveTextContent(String(value));
  });

  it("renders an em dash and muted label when the score is missing", () => {
    render(<ScoreCircle value={null} label="Opportunity" />);

    const circle = screen.getByRole("img", { name: "Opportunity: no score" });
    expect(circle).toHaveAttribute("data-score-tone", "muted");
    expect(circle).toHaveTextContent("—");
  });
});

describe("ScoreBar", () => {
  it.each([
    [95, "high"],
    [72, "good"],
    [41, "warning"],
    [12, "danger"],
  ])("labels %i as %s", (value, tone) => {
    render(<ScoreBar value={value} label="Demand" />);

    const bar = screen.getByLabelText(`Demand: ${value} out of 100, ${tone}`);
    expect(bar).toHaveAttribute("data-score-tone", tone);
    expect(screen.getByText(String(value))).toBeInTheDocument();
  });

  it("clamps fill width to 0..100", () => {
    const { rerender } = render(<ScoreBar value={150} label="Demand" />);

    expect(screen.getByTestId("score-bar-fill")).toHaveStyle({ width: "100%" });

    rerender(<ScoreBar value={-12} label="Demand" />);
    expect(screen.getByTestId("score-bar-fill")).toHaveStyle({ width: "0%" });
  });

  it("renders muted state for NaN scores", () => {
    render(<ScoreBar value={Number.NaN} label="Demand" />);

    const bar = screen.getByLabelText("Demand: no score");
    expect(bar).toHaveAttribute("data-score-tone", "muted");
    expect(bar).toHaveTextContent("—");
  });
});
