// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingClient from "./OnboardingClient";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/components/niche-finder/CityAutocomplete", () => ({
  default: ({
    id,
    value,
    onChange,
    "data-testid": testId = "city-input",
  }: {
    id?: string;
    value: string;
    onChange: (city: string) => void;
    "data-testid"?: string;
  }) => (
    <input
      id={id}
      data-testid={testId}
      role="combobox"
      aria-controls="city-input-options"
      aria-expanded="false"
      value={value}
      onChange={(event) => onChange(event.currentTarget.value)}
      placeholder="City"
    />
  ),
}));

const routing = {
  starter: "easy_win",
  available: ["easy_win", "gbp_blitz", "keyword_hijack"],
  rationale: "Start with one city.",
  next_route: "/",
} as const;

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function setupFetch(
  startReportBody: unknown = {
    status: "success",
    report_id: "rpt_123",
    redirect_url: "/reports/rpt_123?generating=true",
  },
  startReportInit?: ResponseInit,
) {
  const requests: Array<{ url: string; method: string; body: unknown }> = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    requests.push({ url, method, body });

    if (url === "/api/onboarding/profile" && method === "GET") {
      return jsonResponse({ status: "empty", profile: null, target: null });
    }

    if (url === "/api/onboarding/profile" && method === "POST") {
      return jsonResponse({ status: "success", profile: { id: "profile_1" }, routing });
    }

    if (url === "/api/onboarding/target" && method === "POST") {
      return jsonResponse({
        status: "success",
        target: { id: "target_1", ...body },
      });
    }

    if (url === "/api/onboarding/start-report" && method === "POST") {
      return jsonResponse(startReportBody, startReportInit);
    }

    return jsonResponse({ status: "error", message: `Unexpected ${method} ${url}` }, { status: 500 });
  });

  vi.stubGlobal("fetch", fetchMock);
  return { requests, fetchMock };
}

async function beginOnboarding() {
  render(<OnboardingClient />);
  await screen.findByRole("heading", { name: /choose your first market/i });
  await userEvent.click(screen.getByRole("button", { name: /start onboarding/i }));
  await screen.findByRole("heading", { name: /pick the service market/i });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

beforeEach(() => {
  pushMock.mockReset();
});

describe("OnboardingClient", () => {
  it("renders welcome and advances to service", async () => {
    const { requests } = setupFetch();

    await beginOnboarding();

    expect(screen.getByRole("heading", { name: /pick the service market/i })).toBeTruthy();
    expect(requests).toMatchObject([
      { url: "/api/onboarding/profile", method: "GET" },
      {
        url: "/api/onboarding/profile",
        method: "POST",
        body: { intent: "find_first", focus: "niche" },
      },
    ]);
  });

  it("posts the selected starter intent to the profile API", async () => {
    const { requests } = setupFetch();

    render(<OnboardingClient />);
    await screen.findByRole("heading", { name: /choose your first market/i });
    await userEvent.click(screen.getByRole("radio", { name: /agency pipeline/i }));
    await userEvent.click(screen.getByRole("button", { name: /start onboarding/i }));
    await screen.findByRole("heading", { name: /pick the service market/i });

    expect(
      requests.find((request) => request.url === "/api/onboarding/profile" && request.method === "POST"),
    ).toMatchObject({
      body: {
        intent: "coach_agency",
        focus: "agency",
        coach_or_agency: "agency",
      },
    });
  });

  it("selects a custom service and city, then posts profile, target, and start-report payloads", async () => {
    const { requests } = setupFetch();

    await beginOnboarding();
    await userEvent.type(screen.getByTestId("custom-service-input"), "Pool cleaning");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    await screen.findByRole("heading", { name: /choose the market/i });
    const cityField = screen.getByRole("combobox", { name: /city/i });
    expect(screen.getByLabelText(/city/i)).toBe(cityField);
    await userEvent.type(cityField, "Dallas, TX");
    await userEvent.click(screen.getByRole("button", { name: /review target/i }));

    await screen.findByRole("heading", { name: /confirm the first report/i });
    await userEvent.click(screen.getByRole("button", { name: /start report/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/reports/rpt_123?generating=true"));

    expect(requests.find((request) => request.url === "/api/onboarding/profile" && request.method === "POST"))
      .toMatchObject({
        body: { intent: "find_first", focus: "niche" },
      });
    expect(requests.find((request) => request.url === "/api/onboarding/target")).toMatchObject({
      method: "POST",
      body: {
        strategy_id: "easy_win",
        niche_keyword: "Pool cleaning",
        service_category_id: null,
        geo_scope: "city",
        city: "Dallas, TX",
        resolved_label: "Dallas, TX",
        metadata_source: "typed",
      },
    });
    expect(requests.find((request) => request.url === "/api/onboarding/start-report")).toMatchObject({
      method: "POST",
      body: { target_id: "target_1", strategy_id: "easy_win" },
    });
  });

  it("redirects broad targets through cached Explore", async () => {
    setupFetch({
      status: "cached_route_selected",
      code: "broad_target_uses_cached_explore",
      redirect_url: "/explore",
    });

    await beginOnboarding();
    await userEvent.click(screen.getByRole("button", { name: /plumbing/i }));
    await screen.findByRole("heading", { name: /choose the market/i });
    await userEvent.click(screen.getByRole("radio", { name: /broad scan/i }));
    await userEvent.click(screen.getByRole("button", { name: /review target/i }));
    await userEvent.click(await screen.findByRole("button", { name: /continue to explore/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/explore"));
  });

  it("shows fresh-not-included response without redirecting", async () => {
    setupFetch(
      {
        status: "tier_limit",
        code: "fresh_reports_not_included",
        message: "Your current plan can browse cached reports but cannot generate fresh reports.",
      },
      { status: 403 },
    );

    await beginOnboarding();
    await userEvent.type(screen.getByTestId("custom-service-input"), "Locksmith");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));
    await userEvent.type(
      await screen.findByRole("combobox", { name: /city/i }),
      "Tampa, FL",
    );
    await userEvent.click(screen.getByRole("button", { name: /review target/i }));
    await userEvent.click(await screen.findByRole("button", { name: /start report/i }));

    expect(
      await screen.findByText(/cannot generate fresh reports/i),
    ).toBeTruthy();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
