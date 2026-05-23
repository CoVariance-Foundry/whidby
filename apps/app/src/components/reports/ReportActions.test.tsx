// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReportActions from "./ReportActions";
import type { FullReportData } from "@/lib/niche-finder/types";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  rpc: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mocks.push,
    refresh: mocks.refresh,
  }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => ({
    rpc: mocks.rpc,
  })),
}));

const report: FullReportData = {
  id: "rpt_123",
  created_at: "2026-05-22T12:00:00Z",
  spec_version: "1.0",
  niche_keyword: "plumber",
  geo_scope: "metro",
  geo_target: "Phoenix, AZ",
  report_depth: "standard",
  strategy_profile: "easy_win",
  resolved_weights: null,
  keyword_expansion: {
    expanded_keywords: [
      {
        keyword: "emergency plumber near me",
        tier: 1,
        search_volume: 1200,
      },
    ],
  },
  metros: [],
  meta: null,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("ReportActions", () => {
  it("exports the report as JSON", async () => {
    const createObjectURL = vi.fn((blob: Blob) => {
      expect(blob).toBeInstanceOf(Blob);
      return "blob:report";
    });
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<ReportActions report={report} />);
    fireEvent.click(screen.getByRole("button", { name: /export json/i }));

    expect(clickSpy).toHaveBeenCalled();
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0]?.[0];
    expect(blob).toBeDefined();
    if (!blob) throw new Error("Expected export blob");
    const text = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(blob);
    });
    expect(text).toContain('"niche_keyword": "plumber"');
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:report");
  });

  it("confirms deletion before using the supplied modal delete handler", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);

    render(<ReportActions report={report} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: /delete report/i }));
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledWith("rpt_123"));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /delete report/i })).not.toBeDisabled(),
    );
    expect(screen.queryByRole("button", { name: /deleting/i })).not.toBeInTheDocument();
  });

  it("clears a failed delete error when the confirmation is canceled", async () => {
    const onDelete = vi.fn().mockRejectedValue(new Error("Delete failed"));

    render(<ReportActions report={report} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: /delete report/i }));
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    expect(await screen.findByText("Delete failed")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByText("Delete failed")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete report/i })).toBeInTheDocument();
  });

  it("archives the report and returns to reports when archive delete is enabled", async () => {
    mocks.rpc.mockResolvedValue({ data: true, error: null });

    render(<ReportActions report={report} enableArchiveDelete />);
    fireEvent.click(screen.getByRole("button", { name: /delete report/i }));
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() =>
      expect(mocks.rpc).toHaveBeenCalledWith("archive_account_report", {
        p_report_id: "rpt_123",
      }),
    );
    expect(mocks.push).toHaveBeenCalledWith("/reports");
    expect(mocks.refresh).toHaveBeenCalled();
  });
});
