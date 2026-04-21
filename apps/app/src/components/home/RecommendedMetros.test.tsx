// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RecommendedMetros from "./RecommendedMetros";

describe("RecommendedMetros", () => {
  it("renders up to six recommended niches", () => {
    render(
      <RecommendedMetros
        items={[
          { id: "a", niche: "roofing", city: "Phoenix, AZ", score: 78 },
          { id: "b", niche: "plumbing", city: "Austin, TX", score: 71 },
          { id: "c", niche: "concrete", city: "Tulsa, OK", score: 65 },
        ]}
      />,
    );
    expect(screen.getByRole("heading", { name: /recommended/i })).toBeInTheDocument();
    expect(screen.getByText("roofing")).toBeInTheDocument();
    expect(screen.getByText("Phoenix, AZ")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
  });

  it("renders an empty-state note when items is empty", () => {
    render(<RecommendedMetros items={[]} />);
    expect(screen.getByText(/no recommendations yet/i)).toBeInTheDocument();
  });
});
