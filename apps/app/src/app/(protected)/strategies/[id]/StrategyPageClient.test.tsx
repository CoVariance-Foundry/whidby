// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";
import StrategyPageClient from "./StrategyPageClient";

const originalFetch = global.fetch;

afterEach(() => {
  cleanup();
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("StrategyPageClient", () => {
  it("shows a live report recovery card after cached discovery returns zero results", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Low-competition markets.",
      status: "launch",
      input_shape: "city_service",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ markets: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    expect(await screen.findByText("Live report option")).toBeInTheDocument();
    expect(screen.getByText("Run a fresh report for this target")).toBeInTheDocument();
    expect(screen.getAllByText("Boise + plumbing").length).toBeGreaterThan(0);
    expect(screen.getByText(/Live report generation uses 1 monthly report credit/i)).toBeInTheDocument();
    expect(screen.getByText(/Cached discovery returned zero rows/i)).toBeInTheDocument();
  });

  it("sends a fresh strategy run payload from the zero-state live report card", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "keyword_hijack",
      name: "Keyword Hijack",
      description: "Keyword-led markets.",
      status: "launch",
      input_shape: "city_service_keyword",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ markets: [] }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ run_id: "strategy-run-1", status: "queued" }), {
          status: 200,
        }),
      );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.change(screen.getByLabelText("Primary keyword"), {
      target: { value: "boise plumber" },
    });
    fireEvent.click(screen.getByLabelText("Add AI resilience warning filter"));
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await screen.findByText("Live report option");
    fireEvent.click(screen.getByRole("button", { name: /run live report/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/strategies/runs");
    const body = JSON.parse(fetchMock.mock.calls[1][1].body as string);
    expect(body).toEqual({
      mode: "fresh",
      strategy_id: "keyword_hijack",
      city: "Boise",
      service: "plumbing",
      primary_keyword: "boise plumber",
      ai_resilience_filter: true,
      limit: 10,
    });
  });

  it("sends a backend-valid fresh payload for an Expand & Conquer live report", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "expand_conquer",
      name: "Expand & Conquer",
      description: "Reference-market expansion.",
      status: "launch",
      input_shape: "reference_city_service",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ markets: [] }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ run_id: "strategy-run-1", status: "queued" }), {
          status: 200,
        }),
      );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("Reference city id"), {
      target: { value: "boise-id" },
    });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await screen.findByText("Live report option");
    fireEvent.click(screen.getByRole("button", { name: /run live report/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/strategies/runs");
    const body = JSON.parse(fetchMock.mock.calls[1][1].body as string);
    expect(body).toEqual({
      mode: "fresh",
      strategy_id: "expand_conquer",
      city: "boise-id",
      service: "plumbing",
      reference_city_id: "boise-id",
      ai_resilience_filter: false,
      limit: 10,
    });
  });

  it("ignores stale live run responses after a newer zero-result target is loaded", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Low-competition markets.",
      status: "launch",
      input_shape: "city_service",
    };
    let resolveLiveRun: (response: Response) => void = () => undefined;
    const liveRunResponse = new Promise<Response>((resolve) => {
      resolveLiveRun = resolve;
    });
    const fetchMock = vi.fn((url: RequestInfo | URL) => {
      if (String(url) === "/api/strategies/runs") {
        return liveRunResponse;
      }
      return Promise.resolve(new Response(JSON.stringify({ markets: [] }), { status: 200 }));
    });
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await screen.findByText("Live report option");
    expect(screen.getAllByText("Boise + plumbing").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /run live report/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Reno" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(screen.getAllByText("Reno + plumbing").length).toBeGreaterThan(0));

    await act(async () => {
      resolveLiveRun(
        new Response(JSON.stringify({ run_id: "stale-run-1", status: "queued" }), {
          status: 200,
        }),
      );
      await liveRunResponse;
      await Promise.resolve();
    });

    expect(screen.queryByText("stale-run-1")).not.toBeInTheDocument();
    expect(screen.queryByText(/Live report queued/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("Reno + plumbing").length).toBeGreaterThan(0);
  });

  it("renders upgrade-path copy and settings link when fresh runs are not included", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Low-competition markets.",
      status: "launch",
      input_shape: "city_service",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ markets: [] }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "fresh_strategy_runs_not_included",
            status: "tier_limit",
            message: "Your current plan can browse cached strategy results but cannot run fresh strategy discovery.",
            tier: "free",
            monthly_report_limit: 0,
          }),
          { status: 403 },
        ),
      );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await screen.findByText("Live report option");
    fireEvent.click(screen.getByRole("button", { name: /run live report/i }));

    expect(await screen.findByText(/cannot run fresh strategy discovery/i)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /upgrade to run live/i });
    expect(link).toHaveAttribute("href", "/settings");
  });

  it("renders queued state with the run id after a live report run succeeds", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Low-competition markets.",
      status: "launch",
      input_shape: "city_service",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ markets: [] }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "strategy-run-1",
            report_id: "report-1",
            status: "queued",
          }),
          { status: 200 },
        ),
      );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await screen.findByText("Live report option");
    fireEvent.click(screen.getByRole("button", { name: /run live report/i }));

    expect(await screen.findByText(/Live report queued/i)).toBeInTheDocument();
    expect(screen.getByText("strategy-run-1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open report/i })).toHaveAttribute(
      "href",
      "/reports?open=report-1",
    );
  });

  it("sends primary_keyword for keyword_hijack and renders a returned result", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "keyword_hijack",
      name: "Keyword Hijack",
      description: "Keyword-led markets.",
      status: "launch",
      input_shape: "city_service_keyword",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          markets: [
            {
              rank: 1,
              opportunity_score: 86,
              city: { city_id: "boise-id", name: "Boise", state: "ID" },
              service: { service_id: "plumbing", name: "Plumbing" },
              strategy_evidence: {
                search_volume_monthly: 720,
                local_pack_present: true,
              },
              warnings: [{ code: "metric_undersampled" }],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Boise" } });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.change(screen.getByLabelText("Primary keyword"), {
      target: { value: "boise plumber" },
    });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/strategies/discover");
    expect(body).toMatchObject({
      lens_id: "keyword_hijack",
      primary_keyword: "boise plumber",
      ai_resilience_filter: false,
      limit: 10,
    });
    expect(body.city_filters).toEqual([{ field: "name", operator: "like", value: "Boise" }]);
    expect(body.service_filters).toEqual([{ field: "name", operator: "like", value: "plumbing" }]);

    expect(await screen.findByText("Plumbing in Boise")).toBeInTheDocument();
    expect(screen.getByText("search_volume_monthly: 720")).toBeInTheDocument();
    expect(screen.getByText("local_pack_present: yes")).toBeInTheDocument();
    expect(screen.getByText("metric_undersampled")).toBeInTheDocument();
    const score = screen.getByRole("img", { name: "Strategy score: 86 out of 100, high" });
    expect(score).toHaveAttribute("data-score-tone", "high");
    expect(score).toHaveTextContent("86");
  });

  it("sends reference_city_id for Expand & Conquer", async () => {
    const strategy: StrategyCatalogEntry = {
      strategy_id: "expand_conquer",
      name: "Expand & Conquer",
      description: "Reference-market expansion.",
      status: "launch",
      input_shape: "reference_city_service",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ markets: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    render(<StrategyPageClient strategy={strategy} />);

    fireEvent.change(screen.getByLabelText("Reference city id"), {
      target: { value: "boise-id" },
    });
    fireEvent.change(screen.getByLabelText("Service"), { target: { value: "plumbing" } });
    fireEvent.click(screen.getByRole("button", { name: /run discovery/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body).toMatchObject({
      lens_id: "expand_conquer",
      reference_city_id: "boise-id",
    });
    expect(body.service_filters).toEqual([{ field: "name", operator: "like", value: "plumbing" }]);
  });
});
