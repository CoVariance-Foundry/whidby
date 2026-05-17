// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExploreData } from "@/lib/explore/types";
import ExplorePageClient from "./ExplorePageClient";

const originalFetch = global.fetch;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  global.fetch = originalFetch;
});

const fixtureData: ExploreData = {
  cities: [
    {
      cbsa_code: "11111",
      cbsa_name: "Austin-Round Rock-Georgetown, TX",
      state: "TX",
      population: 2_300_000,
      population_class: "metro_1m_5m",
      median_household_income_usd: 91_000,
      owner_occupancy_rate: 0.58,
      median_age_years: 35.8,
      business_density_per_1k: 41.2,
      establishment_growth_yoy: 4.4,
      growth_available: true,
      score_system: "v2",
      best_score: 82,
      presentation_score: 82,
      cached_services_count: 2,
      best_opportunity_score: 82,
      average_opportunity_score: 75,
      cached_scores: [
        {
          report_id: "report-austin-roofing",
          service: "roofing",
          opportunity_score: 82,
          archetype_id: "PACK_VULN",
          archetype_label: "Pack, vulnerable",
          last_scored_at: "2026-05-01T12:00:00Z",
          confidence_score: 88,
          ai_resilience_score: 72,
          ai_exposure: "AI_MINIMAL",
          difficulty_tier: "MODERATE",
          refresh_target_id: "target-austin-roofing",
          last_refreshed_at: "2026-05-01T12:30:00Z",
          next_refresh_at: "2026-05-31T12:30:00Z",
          stale_after_days: 30,
          is_stale: true,
          opportunity_delta: 6,
        },
        {
          report_id: "report-austin-plumbing",
          service: "plumbing",
          opportunity_score: 68,
          archetype_id: "FRAG_WEAK",
          archetype_label: "Fragmented, weak",
          last_scored_at: "2026-05-02T12:00:00Z",
          refresh_target_id: "target-austin-roofing",
        },
      ],
    },
    {
      cbsa_code: "22222",
      cbsa_name: "Phoenix-Mesa-Chandler, AZ",
      state: "AZ",
      population: 4_900_000,
      population_class: "metro_1m_5m",
      median_household_income_usd: 82_000,
      owner_occupancy_rate: 0.64,
      median_age_years: 37.4,
      business_density_per_1k: 34.1,
      establishment_growth_yoy: 1.2,
      growth_available: true,
      score_system: "v2",
      best_score: 91,
      presentation_score: 91,
      cached_services_count: 1,
      best_opportunity_score: 91,
      average_opportunity_score: 91,
      cached_scores: [
        {
          report_id: "report-phoenix-hvac",
          service: "hvac",
          opportunity_score: 91,
          archetype_id: "PACK_EST",
          archetype_label: "Pack, established",
          last_scored_at: "2026-05-03T12:00:00Z",
          refresh_target_id: "target-phoenix-hvac",
          last_refreshed_at: "2026-05-03T12:30:00Z",
          next_refresh_at: "2026-06-02T12:30:00Z",
          stale_after_days: 30,
          is_stale: false,
          opportunity_delta: null,
        },
      ],
    },
    {
      cbsa_code: "33333",
      cbsa_name: "Reno, NV",
      state: "NV",
      population: 520_000,
      population_class: "metro_250k_1m",
      median_household_income_usd: 70_000,
      owner_occupancy_rate: null,
      median_age_years: null,
      business_density_per_1k: null,
      establishment_growth_yoy: null,
      growth_available: false,
      score_system: "none",
      best_score: null,
      presentation_score: null,
      cached_services_count: 0,
      best_opportunity_score: null,
      average_opportunity_score: null,
      cached_scores: [],
    },
  ],
};

function cityRows() {
  return screen
    .getAllByRole("row")
    .filter((row) => row.getAttribute("aria-label")?.startsWith("Open "));
}

function openAustinFreshScan(serviceNames: string[]) {
  fireEvent.click(screen.getByRole("row", { name: /open austin/i }));
  serviceNames.forEach((serviceName) => {
    fireEvent.click(screen.getByLabelText(`Select ${serviceName} for fresh scan`));
  });
  fireEvent.click(screen.getByRole("button", { name: /open fresh scan confirmation/i }));
  return screen.getByRole("dialog", { name: /confirm fresh scan/i });
}

function pressTab(shiftKey = false) {
  fireEvent.keyDown(document, { key: "Tab", shiftKey });
}

describe("ExplorePageClient", () => {
  it("filters by service and sorts city rows", () => {
    render(<ExplorePageClient data={fixtureData} />);

    expect(cityRows()[0].textContent).toContain("Phoenix-Mesa-Chandler");

    fireEvent.change(screen.getByLabelText("Filter by cached service"), {
      target: { value: "plumbing" },
    });
    expect(screen.getByRole("row", { name: /open austin/i })).toBeTruthy();
    expect(screen.queryByRole("row", { name: /open phoenix/i })).toBeNull();

    fireEvent.change(screen.getByLabelText("Filter by cached service"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sort by Population" }));
    expect(cityRows()[0].textContent).toContain("Phoenix-Mesa-Chandler");
    fireEvent.click(screen.getByRole("button", { name: "Sort by Population" }));
    expect(cityRows()[0].textContent).toContain("Reno");
  });

  it("opens the city drawer with row keyboard activation", () => {
    render(<ExplorePageClient data={fixtureData} />);

    fireEvent.keyDown(screen.getByRole("row", { name: /open austin/i }), {
      key: "Enter",
    });

    expect(screen.getByRole("dialog", { name: /austin-round rock/i })).toBeTruthy();
    expect(screen.getByText("Median income")).toBeTruthy();
    expect(screen.getAllByText("$91,000").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /open cached report for roofing/i }).getAttribute("href")).toBe(
      "/reports?open=report-austin-roofing",
    );
  });

  it("moves focus into the city drawer and closes it on Escape", () => {
    render(<ExplorePageClient data={fixtureData} />);

    const phoenixRow = screen.getByRole("row", { name: /open phoenix/i });
    phoenixRow.focus();
    fireEvent.click(phoenixRow);

    const closeButton = screen.getByRole("button", { name: "Close city drawer" });
    expect(document.activeElement).toBe(closeButton);
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: /phoenix-mesa/i })).toBeNull();
    expect(document.body.style.overflow).toBe("");
    expect(document.activeElement).toBe(phoenixRow);
  });

  it("wraps Tab focus inside the city drawer", () => {
    render(<ExplorePageClient data={fixtureData} />);

    fireEvent.click(screen.getByRole("row", { name: /open austin/i }));

    const closeButton = screen.getByRole("button", { name: "Close city drawer" });
    const lastFocusable = screen.getByLabelText("Select plumbing for fresh scan");

    lastFocusable.focus();
    pressTab();
    expect(document.activeElement).toBe(closeButton);

    closeButton.focus();
    pressTab(true);
    expect(document.activeElement).toBe(lastFocusable);
  });

  it("posts one fresh scan per selected cached service with city, service, and state", async () => {
    const fetchMock = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      const body = JSON.parse(init?.body as string) as { service: string };
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "success",
            query: body,
            score_result: { opportunity_score: 80, classification_label: "High" },
            report_id: `fresh-${body.service}-report`,
          }),
          { status: 200 },
        ),
      );
    });
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);
    const dialog = openAustinFreshScan(["roofing", "plumbing"]);

    fireEvent.click(within(dialog).getByRole("button", { name: /confirm fresh scan for 2 services/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls.map((call) => JSON.parse(call[1]?.body as string))).toEqual([
      {
        city: "Austin-Round Rock-Georgetown",
        service: "roofing",
        state: "TX",
      },
      {
        city: "Austin-Round Rock-Georgetown",
        service: "plumbing",
        state: "TX",
      },
    ]);
  });

  it("posts one selected refresh run with refreshable selected services and filters", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ run_id: "refresh-run-123", status: "queued" }), {
          status: 202,
        }),
      ),
    );
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);

    fireEvent.change(screen.getByLabelText("Filter by cached service"), {
      target: { value: "roofing" },
    });
    fireEvent.click(screen.getByRole("row", { name: /open austin/i }));
    const drawer = screen.getByRole("dialog", { name: /austin-round rock/i });
    fireEvent.click(screen.getByLabelText("Select roofing for fresh scan"));
    fireEvent.click(screen.getByLabelText("Select plumbing for fresh scan"));
    const refreshSelectedButton = within(drawer).getByRole("button", {
      name: "Refresh selected",
    });
    act(() => {
      refreshSelectedButton.click();
      refreshSelectedButton.click();
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/explore/refresh/runs",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
    const requestInit = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(JSON.parse(requestInit.body as string)).toEqual({
      scope: "selected",
      target_ids: ["target-austin-roofing"],
      filters: {
        population_min: null,
        population_max: null,
        income_min: null,
        income_max: null,
        selected_states: [],
        service: "roofing",
        growing_only: false,
      },
      flags: {
        force: false,
        dry_run: false,
        strategy_profile: "balanced",
        max_items: 2,
        concurrency: 2,
      },
    });
    expect(screen.getByRole("link", { name: /view refresh run refresh-run-123/i }).getAttribute("href")).toBe(
      "/explore?refresh_run=refresh-run-123",
    );
    expect(screen.getByText(/refresh-run-123 queued/i)).toBeTruthy();
  });

  it("renders successful fresh scan report links", async () => {
    const fetchMock = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      const body = JSON.parse(init?.body as string) as { service: string };
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "success",
            query: body,
            score_result: { opportunity_score: 80, classification_label: "High" },
            report_id: `fresh-${body.service}-report`,
          }),
          { status: 200 },
        ),
      );
    });
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);
    const dialog = openAustinFreshScan(["roofing", "plumbing"]);

    fireEvent.click(within(dialog).getByRole("button", { name: /confirm fresh scan for 2 services/i }));

    await waitFor(() => {
      expect(within(dialog).getByText("roofing scan succeeded")).toBeTruthy();
      expect(within(dialog).getByText("plumbing scan succeeded")).toBeTruthy();
    });

    expect(within(dialog).getByRole("link", { name: /open fresh report for roofing/i }).getAttribute("href")).toBe(
      "/reports?open=fresh-roofing-report",
    );
    expect(within(dialog).getByRole("link", { name: /open fresh report for plumbing/i }).getAttribute("href")).toBe(
      "/reports?open=fresh-plumbing-report",
    );
  });

  it("shows partial fresh scan failures without hiding successful report links", async () => {
    const fetchMock = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      const body = JSON.parse(init?.body as string) as { service: string };
      if (body.service === "plumbing") {
        return Promise.resolve(
          new Response(JSON.stringify({ status: "unavailable", message: "Pipeline down." }), {
            status: 503,
          }),
        );
      }

      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "success",
            query: body,
            score_result: { opportunity_score: 84, classification_label: "High" },
            report_id: "fresh-roofing-report",
          }),
          { status: 200 },
        ),
      );
    });
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);
    const dialog = openAustinFreshScan(["roofing", "plumbing"]);

    fireEvent.click(within(dialog).getByRole("button", { name: /confirm fresh scan for 2 services/i }));

    await waitFor(() => {
      expect(within(dialog).getByText("roofing scan succeeded")).toBeTruthy();
      expect(within(dialog).getByText("plumbing scan failed")).toBeTruthy();
    });

    expect(within(dialog).getByRole("link", { name: /open fresh report for roofing/i }).getAttribute("href")).toBe(
      "/reports?open=fresh-roofing-report",
    );
    expect(within(dialog).getByText("Pipeline down.")).toBeTruthy();
    expect(within(dialog).queryByRole("link", { name: /open fresh report for plumbing/i })).toBeNull();
  });

  it("blocks duplicate fresh scan confirmation while requests are loading", async () => {
    let resolveFetch: (response: Response) => void = () => undefined;
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    const fetchMock = vi.fn(() => pendingResponse);
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);
    const dialog = openAustinFreshScan(["roofing"]);
    const confirmButton = within(dialog).getByRole("button", {
      name: /confirm fresh scan for 1 services/i,
    });

    fireEvent.click(confirmButton);

    expect((confirmButton as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(confirmButton);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolveFetch(
      new Response(
        JSON.stringify({
          status: "success",
          query: {
            city: "Austin-Round Rock-Georgetown",
            service: "roofing",
            state: "TX",
          },
          score_result: { opportunity_score: 80, classification_label: "High" },
          report_id: "fresh-roofing-report",
        }),
        { status: 200 },
      ),
    );

    await waitFor(() => {
      expect(within(dialog).getByRole("link", { name: /open fresh report for roofing/i })).toBeTruthy();
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("ignores stale fresh scan results after switching cities", async () => {
    let resolveAustinScan: (response: Response) => void = () => undefined;
    const pendingAustinScan = new Promise<Response>((resolve) => {
      resolveAustinScan = resolve;
    });
    const fetchMock = vi.fn(() => pendingAustinScan);
    global.fetch = fetchMock;

    render(<ExplorePageClient data={fixtureData} />);
    const austinDialog = openAustinFreshScan(["roofing"]);
    fireEvent.click(
      within(austinDialog).getByRole("button", {
        name: /confirm fresh scan for 1 services/i,
      }),
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(within(austinDialog).getByRole("button", { name: "Cancel fresh scan" }));
    fireEvent.click(screen.getByRole("button", { name: "Close city drawer" }));
    fireEvent.click(screen.getByRole("row", { name: /open phoenix/i }));
    fireEvent.click(screen.getByLabelText("Select hvac for fresh scan"));
    fireEvent.click(screen.getByRole("button", { name: /open fresh scan confirmation/i }));
    const phoenixDialog = screen.getByRole("dialog", { name: /confirm fresh scan/i });

    await act(async () => {
      resolveAustinScan(
        new Response(
          JSON.stringify({
            status: "success",
            query: {
              city: "Austin-Round Rock-Georgetown",
              service: "roofing",
              state: "TX",
            },
            score_result: { opportunity_score: 80, classification_label: "High" },
            report_id: "fresh-roofing-report",
          }),
          { status: 200 },
        ),
      );
      await pendingAustinScan;
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(within(phoenixDialog).getByText("hvac")).toBeTruthy();
    expect(within(phoenixDialog).queryByText("roofing scan succeeded")).toBeNull();
    expect(within(phoenixDialog).queryByRole("link", { name: /open fresh report for roofing/i })).toBeNull();
  });

  it("moves focus into fresh scan confirmation and closes only the modal on Escape", () => {
    render(<ExplorePageClient data={fixtureData} />);

    const austinRow = screen.getByRole("row", { name: /open austin/i });
    austinRow.focus();
    fireEvent.click(austinRow);
    fireEvent.click(screen.getByLabelText("Select roofing for fresh scan"));
    const freshScanButton = screen.getByRole("button", {
      name: /open fresh scan confirmation/i,
    });
    const drawer = screen.getByRole("dialog", { name: /austin-round rock/i });
    expect(drawer.getAttribute("aria-modal")).toBe("true");

    fireEvent.click(freshScanButton);

    const closeButton = screen.getByRole("button", { name: "Close fresh scan dialog" });
    expect(document.activeElement).toBe(closeButton);
    expect(screen.getByRole("dialog", { name: /confirm fresh scan/i })).toBeTruthy();
    expect(drawer.getAttribute("aria-modal")).toBe("false");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: /confirm fresh scan/i })).toBeNull();
    expect(screen.getByRole("dialog", { name: /austin-round rock/i })).toBeTruthy();
    expect(drawer.getAttribute("aria-modal")).toBe("true");
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.activeElement).toBe(freshScanButton);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: /austin-round rock/i })).toBeNull();
    expect(document.body.style.overflow).toBe("");
    expect(document.activeElement).toBe(austinRow);
  });

  it("wraps Tab focus inside the nested fresh scan confirmation", () => {
    render(<ExplorePageClient data={fixtureData} />);

    fireEvent.click(screen.getByRole("row", { name: /open austin/i }));
    fireEvent.click(screen.getByLabelText("Select roofing for fresh scan"));
    const freshScanButton = screen.getByRole("button", {
      name: /open fresh scan confirmation/i,
    });

    fireEvent.click(freshScanButton);

    const drawerCloseButton = screen.getByRole("button", { name: "Close city drawer" });
    const confirmation = screen.getByRole("dialog", { name: /confirm fresh scan/i });
    const closeButton = within(confirmation).getByRole("button", {
      name: "Close fresh scan dialog",
    });
    const confirmButton = within(confirmation).getByRole("button", {
      name: /confirm fresh scan for 1 services/i,
    });

    confirmButton.focus();
    pressTab();
    expect(document.activeElement).toBe(closeButton);

    closeButton.focus();
    pressTab(true);
    expect(document.activeElement).toBe(confirmButton);

    drawerCloseButton.focus();
    pressTab();
    expect(document.activeElement).toBe(closeButton);
  });

  it("shows empty state and reset restores results", () => {
    render(<ExplorePageClient data={fixtureData} />);

    fireEvent.change(screen.getByLabelText("Minimum population"), {
      target: { value: "99999999" },
    });

    expect(screen.getByText(/no cities match/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));

    expect(screen.getByRole("row", { name: /open phoenix/i })).toBeTruthy();
    expect(screen.getByRole("row", { name: /open austin/i })).toBeTruthy();
  });
});
