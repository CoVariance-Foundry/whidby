// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import NicheFinderTabs from "./NicheFinderTabs";

afterEach(() => {
  cleanup();
});

describe("NicheFinderTabs", () => {
  it("renders both tabs with the correct aria-selected state", () => {
    render(<NicheFinderTabs active="niche" onChange={() => {}} />);
    const nicheTab = screen.getByRole("tab", { name: /niche & city/i });
    const strategyTab = screen.getByRole("tab", { name: /strategy/i });
    expect(nicheTab).toHaveAttribute("aria-selected", "true");
    expect(strategyTab).toHaveAttribute("aria-selected", "false");
  });

  it("calls onChange with the clicked tab key", async () => {
    const onChange = vi.fn();
    render(<NicheFinderTabs active="niche" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: /strategy/i }));
    expect(onChange).toHaveBeenCalledWith("strategy");
  });
});
