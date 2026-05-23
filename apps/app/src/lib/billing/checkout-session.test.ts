import type { SupabaseClient } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";
import { reserveCheckoutSession } from "./checkout-session";

describe("reserveCheckoutSession", () => {
  it("returns the pending same-plan reservation when insert loses the unique-index race", async () => {
    const existingReservation = {
      id: "reservation-race",
      account_id: "account-1",
      user_id: "user-1",
      plan_key: "plus",
      status: "pending",
      stripe_checkout_session_id: null,
      stripe_checkout_url: null,
      expires_at: "2026-05-01T00:30:00.000Z",
      idempotency_key: "billing-checkout:account-1:plus:reservation-race",
    };
    const single = vi.fn().mockResolvedValue({
      data: null,
      error: {
        code: "23505",
        message:
          "duplicate key value violates unique constraint idx_billing_checkout_sessions_one_pending_account",
      },
    });
    const insertSelect = vi.fn(() => ({ single }));
    const insert = vi.fn(() => ({ select: insertSelect }));

    type RecoveryBuilder = {
      eq: (column: string, value: unknown) => RecoveryBuilder;
      gt: (column: string, value: unknown) => RecoveryBuilder;
      order: (column: string, options: { ascending: boolean }) => RecoveryBuilder;
      limit: (count: number) => RecoveryBuilder;
      maybeSingle: () => Promise<{ data: typeof existingReservation; error: null }>;
    };
    const recoveryBuilder = {} as RecoveryBuilder;
    recoveryBuilder.eq = vi.fn(() => recoveryBuilder);
    recoveryBuilder.gt = vi.fn(() => recoveryBuilder);
    recoveryBuilder.order = vi.fn(() => recoveryBuilder);
    recoveryBuilder.limit = vi.fn(() => recoveryBuilder);
    recoveryBuilder.maybeSingle = vi.fn().mockResolvedValue({
      data: existingReservation,
      error: null,
    });
    const select = vi.fn(() => recoveryBuilder);

    const from = vi
      .fn()
      .mockReturnValueOnce({ insert })
      .mockReturnValueOnce({ select });
    const supabase = { from } as unknown as SupabaseClient;

    const reservation = await reserveCheckoutSession(supabase, {
      account_id: "account-1",
      user_id: "user-1",
      plan_key: "plus",
      now: new Date("2026-05-01T00:00:00.000Z"),
    });

    expect(reservation).toEqual(existingReservation);
    expect(from).toHaveBeenNthCalledWith(1, "billing_checkout_sessions");
    expect(from).toHaveBeenNthCalledWith(2, "billing_checkout_sessions");
    expect(recoveryBuilder.eq).toHaveBeenCalledWith("account_id", "account-1");
    expect(recoveryBuilder.eq).toHaveBeenCalledWith("plan_key", "plus");
    expect(recoveryBuilder.eq).toHaveBeenCalledWith("status", "pending");
    expect(recoveryBuilder.gt).toHaveBeenCalledWith(
      "expires_at",
      "2026-05-01T00:00:00.000Z",
    );
  });
});
