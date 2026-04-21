// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HeroQuickSearch from "./HeroQuickSearch";

describe("HeroQuickSearch", () => {
  it("shows the prompt copy and a link to the niche finder", () => {
    render(<HeroQuickSearch />);
    expect(
      screen.getByText(/start a niche scoring run/i),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /open niche finder/i });
    expect(link).toHaveAttribute("href", "/niche-finder");
  });
});
