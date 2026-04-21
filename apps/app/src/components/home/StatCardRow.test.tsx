// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatCardRow from "./StatCardRow";

describe("StatCardRow", () => {
  it("renders four stats with labels and values", () => {
    render(
      <StatCardRow
        stats={[
          { label: "Niches scored", value: "42" },
          { label: "Watchlist", value: "8" },
          { label: "Avg score", value: "67" },
          { label: "Reports", value: "38" },
        ]}
      />,
    );
    expect(screen.getByText("Niches scored")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Watchlist")).toBeInTheDocument();
    expect(screen.getByText("67")).toBeInTheDocument();
    expect(screen.getByText("38")).toBeInTheDocument();
  });

  it("renders an optional delta below the value when provided", () => {
    render(
      <StatCardRow
        stats={[
          { label: "Reports", value: "42", delta: "+3 this week" },
        ]}
      />,
    );
    expect(screen.getByText("+3 this week")).toBeInTheDocument();
  });
});
