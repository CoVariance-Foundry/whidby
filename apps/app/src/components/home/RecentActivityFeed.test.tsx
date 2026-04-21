// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RecentActivityFeed from "./RecentActivityFeed";

describe("RecentActivityFeed", () => {
  it("renders items with timestamp-formatted dates", () => {
    render(
      <RecentActivityFeed
        items={[
          {
            id: "r1",
            niche: "roofing",
            city: "Phoenix, AZ",
            created_at: "2026-04-20T12:00:00Z",
          },
        ]}
      />,
    );
    expect(screen.getByText(/roofing · Phoenix, AZ/i)).toBeInTheDocument();
    // formatted "Apr 20" or "2026-04-20" is acceptable — just ensure a year/month fragment shows
    expect(screen.getByText(/2026|apr/i)).toBeInTheDocument();
  });

  it("shows empty state when items is empty", () => {
    render(<RecentActivityFeed items={[]} />);
    expect(screen.getByText(/no recent activity/i)).toBeInTheDocument();
  });
});
