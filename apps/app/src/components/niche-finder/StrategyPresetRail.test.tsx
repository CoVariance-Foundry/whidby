// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import StrategyPresetRail from "./StrategyPresetRail";

afterEach(() => {
  cleanup();
});

describe("StrategyPresetRail", () => {
  it("renders all 8 archetype cards", () => {
    render(<StrategyPresetRail onPick={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(8);
  });

  it("calls onPick with the archetype id when clicked", async () => {
    const onPick = vi.fn();
    render(<StrategyPresetRail onPick={onPick} />);
    const user = userEvent.setup();
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]);
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(typeof onPick.mock.calls[0][0]).toBe("string");
  });
});
