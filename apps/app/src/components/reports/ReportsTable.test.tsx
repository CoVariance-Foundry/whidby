// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect } from "vitest";
import ReportsTable, { type TableRow } from "./ReportsTable";

afterEach(cleanup);

const rows: TableRow[] = [
  {
    id: "r1",
    niche: "roofing",
    city: "Phoenix, AZ",
    archetype_id: "PACK_VULN",
    archetype_short: "Pack, vulnerable",
    opportunity_score: 78,
    spec_version: "1.1",
    created_at: "2026-04-20T12:00:00Z",
  },
  {
    id: "r2",
    niche: "plumbing",
    city: "Austin, TX",
    archetype_id: "FRAG_WEAK",
    archetype_short: "Fragmented, weak",
    opportunity_score: 62,
    spec_version: "1.1",
    created_at: "2026-04-19T09:00:00Z",
  },
];

describe("ReportsTable", () => {
  it("renders a row for each item", () => {
    render(<ReportsTable rows={rows} />);
    expect(screen.getByText(/roofing/)).toBeInTheDocument();
    expect(screen.getByText(/plumbing/)).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
  });

  it("shows empty state when rows is empty", () => {
    render(<ReportsTable rows={[]} />);
    expect(screen.getByText(/no reports match/i)).toBeInTheDocument();
  });
});
