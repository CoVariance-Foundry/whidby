// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, describe, it, expect, vi } from "vitest";

expect.extend(matchers);
import PinnedRecentRail from "./PinnedRecentRail";

afterEach(cleanup);

describe("PinnedRecentRail", () => {
  it("renders pinned and recent sections with items", () => {
    render(
      <PinnedRecentRail
        pinned={[{ city: "Austin, TX", service: "plumber", at: 1 }]}
        recent={[{ city: "Phoenix, AZ", service: "roofing", at: 2 }]}
        onPick={() => {}}
      />,
    );
    expect(screen.getByText("Austin, TX")).toBeInTheDocument();
    expect(screen.getByText("plumber")).toBeInTheDocument();
    expect(screen.getByText("Phoenix, AZ")).toBeInTheDocument();
    expect(screen.getByText("roofing")).toBeInTheDocument();
  });

  it("shows empty states when no entries exist", () => {
    render(<PinnedRecentRail pinned={[]} recent={[]} onPick={() => {}} />);
    expect(screen.getByText(/no pinned/i)).toBeInTheDocument();
    expect(screen.getByText(/no recent/i)).toBeInTheDocument();
  });

  it("calls onPick when a recent item is clicked", async () => {
    const onPick = vi.fn();
    render(
      <PinnedRecentRail
        pinned={[]}
        recent={[{ city: "Phoenix, AZ", service: "roofing", at: 1 }]}
        onPick={onPick}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /phoenix.*roofing/i }));
    expect(onPick).toHaveBeenCalledWith({ city: "Phoenix, AZ", service: "roofing", at: 1 });
  });
});
