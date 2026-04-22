// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect } from "vitest";
import SignalRow from "./SignalRow";
import type { SignalDefinition } from "@/lib/reports/signal-definitions";

afterEach(cleanup);

const baseDef: SignalDefinition = {
  label: "Test signal",
  format: "number",
  direction: "higher_better",
  description: "A test signal description.",
};

describe("SignalRow", () => {
  it("renders the label and description", () => {
    render(<SignalRow definition={baseDef} value={42} />);
    expect(screen.getByText("Test signal")).toBeInTheDocument();
    expect(screen.getByText("A test signal description.")).toBeInTheDocument();
  });

  it("formats number values", () => {
    render(<SignalRow definition={baseDef} value={42.567} />);
    expect(screen.getByText("42.6")).toBeInTheDocument();
  });

  it("formats percent values (0-1 range)", () => {
    const def = { ...baseDef, format: "percent" as const };
    render(<SignalRow definition={def} value={0.73} />);
    expect(screen.getByText("73%")).toBeInTheDocument();
  });

  it("formats currency values", () => {
    const def = { ...baseDef, format: "currency" as const };
    render(<SignalRow definition={def} value={12.5} />);
    expect(screen.getByText("$12.50")).toBeInTheDocument();
  });

  it("formats boolean true", () => {
    const def = { ...baseDef, format: "boolean" as const };
    render(<SignalRow definition={def} value={true} />);
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("formats boolean false", () => {
    const def = { ...baseDef, format: "boolean" as const };
    render(<SignalRow definition={def} value={false} />);
    expect(screen.getByText("No")).toBeInTheDocument();
  });

  it("formats count values with commas for large numbers", () => {
    const def = { ...baseDef, format: "count" as const };
    render(<SignalRow definition={def} value={12500} />);
    expect(screen.getByText("12,500")).toBeInTheDocument();
  });

  it("shows dash for null values", () => {
    render(<SignalRow definition={baseDef} value={null} />);
    expect(screen.getByText("--")).toBeInTheDocument();
  });
});
