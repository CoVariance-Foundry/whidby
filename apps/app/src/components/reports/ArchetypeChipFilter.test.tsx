// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect, vi } from "vitest";
import ArchetypeChipFilter from "./ArchetypeChipFilter";

afterEach(cleanup);

describe("ArchetypeChipFilter", () => {
  it("renders 'All strategies' + 8 archetype chips", () => {
    render(<ArchetypeChipFilter selected={[]} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /all strategies/i })).toBeInTheDocument();
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(9); // 1 All + 8 archetypes
  });

  it("calls onChange with toggled selection when a chip is clicked", async () => {
    const onChange = vi.fn();
    render(<ArchetypeChipFilter selected={[]} onChange={onChange} />);
    const user = userEvent.setup();
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(Array.isArray(onChange.mock.calls[0][0])).toBe(true);
  });

  it("clears selection when 'All strategies' is clicked", async () => {
    const onChange = vi.fn();
    render(<ArchetypeChipFilter selected={["PACK_VULN", "FRAG_WEAK"]} onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /all strategies/i }));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
