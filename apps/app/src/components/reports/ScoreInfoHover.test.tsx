// @vitest-environment jsdom
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect } from "vitest";
import ScoreInfoHover from "./ScoreInfoHover";
import { SCORE_EXPLAINERS, type ScoreKey } from "@/lib/reports/score-explainers";

afterEach(cleanup);

describe("ScoreInfoHover", () => {
  it("renders an info button with accessible label", () => {
    render(<ScoreInfoHover scoreKey="demand" />);
    expect(screen.getByRole("button", { name: /what is demand/i })).toBeInTheDocument();
  });

  it("does not show tooltip by default", () => {
    render(<ScoreInfoHover scoreKey="demand" />);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("shows tooltip on click", () => {
    render(<ScoreInfoHover scoreKey="organic_competition" />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(screen.getByText("Organic Competition")).toBeInTheDocument();
  });

  it("shows correct content for each score key", () => {
    const keys: ScoreKey[] = [
      "demand",
      "organic_competition",
      "local_competition",
      "monetization",
      "ai_resilience",
      "opportunity",
    ];

    for (const key of keys) {
      const { unmount } = render(<ScoreInfoHover scoreKey={key} />);
      fireEvent.click(screen.getByRole("button"));
      const explainer = SCORE_EXPLAINERS[key];
      expect(screen.getByText(explainer.title)).toBeInTheDocument();
      expect(screen.getByText(explainer.definition)).toBeInTheDocument();
      expect(screen.getByText(explainer.howToRead)).toBeInTheDocument();
      for (const band of explainer.bands) {
        expect(screen.getByText(band.label)).toBeInTheDocument();
      }
      unmount();
    }
  });

  it("closes tooltip when clicking the button again", () => {
    render(<ScoreInfoHover scoreKey="monetization" />);
    const btn = screen.getByRole("button");
    fireEvent.click(btn);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("renders three color bands in tooltip", () => {
    render(<ScoreInfoHover scoreKey="local_competition" />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Hard")).toBeInTheDocument();
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.getByText("Easy")).toBeInTheDocument();
  });

  it("competition scores show inverse-direction language", () => {
    render(<ScoreInfoHover scoreKey="organic_competition" />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/weaker competition/i)).toBeInTheDocument();
  });

  it("closes on outside click", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <ScoreInfoHover scoreKey="demand" />
        <button data-testid="outside">outside</button>
      </div>,
    );
    fireEvent.click(screen.getByRole("button", { name: /what is demand/i }));
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    await user.click(screen.getByTestId("outside"));
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("sets aria-describedby when open", () => {
    render(<ScoreInfoHover scoreKey="ai_resilience" />);
    const btn = screen.getByRole("button");
    expect(btn).not.toHaveAttribute("aria-describedby");
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-describedby");
    const tooltipId = btn.getAttribute("aria-describedby")!;
    expect(document.getElementById(tooltipId)).toBeInTheDocument();
  });
});
