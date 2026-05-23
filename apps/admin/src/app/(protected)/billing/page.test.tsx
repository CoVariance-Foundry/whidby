// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BillingIssuesPage from "./page";

const issue = {
  id: "issue-1",
  severity: "error",
  status: "open",
  event_type: "checkout_failed",
  source: "checkout",
  account_id: "account-1",
  user_id: "user-1",
  stripe_customer_id: "cus_123",
  stripe_subscription_id: null,
  stripe_checkout_session_id: "cs_123",
  stripe_event_id: null,
  public_message: "Billing checkout could not start.",
  internal_message: "Stripe configuration missing",
  metadata: { plan_key: "plus" },
  created_at: "2026-05-22T20:00:00.000Z",
  resolved_at: null,
};

describe("BillingIssuesPage", () => {
  beforeEach(() => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/resolve")) {
        return Promise.resolve(new Response(JSON.stringify({ status: "success" }), { status: 200 }));
      }
      return Promise.resolve(
        new Response(JSON.stringify({ status: "success", issues: [issue] }), { status: 200 }),
      );
    }) as never;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders billing issue counts, details, and resolve action", async () => {
    render(<BillingIssuesPage />);

    await screen.findByText("Billing checkout could not start.");
    expect(screen.getByText("checkout_failed")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /toggle checkout_failed/i }));
    expect(screen.getByText("Stripe configuration missing")).toBeInTheDocument();
    expect(screen.getByText(/plan_key/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /mark resolved/i }));
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/billing/issues/issue-1/resolve", {
        method: "POST",
      });
    });
  });

  it("prevents duplicate resolve requests while one is in flight", async () => {
    let resolvePost!: (response: Response) => void;
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/resolve")) {
        return new Promise<Response>((resolve) => {
          resolvePost = resolve;
        });
      }
      return Promise.resolve(
        new Response(JSON.stringify({ status: "success", issues: [issue] }), { status: 200 }),
      );
    }) as never;

    render(<BillingIssuesPage />);

    await screen.findByText("Billing checkout could not start.");
    const button = screen.getByRole("button", { name: /mark resolved/i });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(screen.getByRole("button", { name: /resolving/i })).toBeDisabled();
    const resolveCalls = vi.mocked(global.fetch).mock.calls.filter(([input]) =>
      String(input).includes("/resolve"),
    );
    expect(resolveCalls).toHaveLength(1);

    resolvePost(new Response(JSON.stringify({ status: "success" }), { status: 200 }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /mark resolved/i })).toBeEnabled();
    });
  });
});
