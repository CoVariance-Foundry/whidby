// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SavedSearchesBlock from "./SavedSearchesBlock";

describe("SavedSearchesBlock", () => {
  it("shows coming-soon empty state", () => {
    render(<SavedSearchesBlock />);
    expect(screen.getByRole("heading", { name: /saved searches/i })).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });
});
