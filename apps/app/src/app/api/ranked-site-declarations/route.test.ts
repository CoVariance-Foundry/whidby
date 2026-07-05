import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

vi.mock("@/lib/account/entitlements", () => {
  class EntitlementError extends Error {
    constructor(
      message: string,
      public readonly status: number,
      public readonly code: string,
    ) {
      super(message);
    }
  }
  return {
    EntitlementError,
    resolveEntitlementContext: mocks.resolveEntitlementContext,
  };
});

import { EntitlementError } from "@/lib/account/entitlements";
import { GET, PATCH, POST } from "./route";

describe("/api/ranked-site-declarations", () => {
  const user = {
    id: "44444444-4444-4444-4444-444444444444",
    email: "user@example.com",
  };
  const entitlement = {
    account_id: "33333333-3333-3333-3333-333333333333",
    member_role: "owner",
    plan_key: "plus",
    monthly_report_limit: 10,
    subscription_status: "active",
    current_period_start: "2026-05-01T00:00:00.000Z",
    current_period_end: "2026-06-01T00:00:00.000Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.resolveEntitlementContext.mockResolvedValue({ user, entitlement });
  });

  it("requires authentication before reading declarations", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);
    mocks.resolveEntitlementContext.mockRejectedValueOnce(
      new EntitlementError("Authentication required.", 401, "auth_required"),
    );

    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(401);
    expect(body).toEqual({
      status: "entitlement_error",
      code: "auth_required",
      message: "Authentication required.",
    });
    expect(supabase.listSelect).not.toHaveBeenCalled();
  });

  it("returns account declarations with Expand & Conquer unlock state", async () => {
    const declarations = [
      declaration({ id: "declared", active: true, proof_state: "declared" }),
      declaration({ id: "inactive", active: false, proof_state: "verified" }),
    ];
    const supabase = createSupabaseMock({
      listResult: { data: declarations, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      declarations,
      unlock: {
        requirement_id: "ranked_site_declaration",
        expand_conquer_unlocked: true,
        unlocked_strategy_ids: ["expand_conquer"],
        active_declaration_id: "declared",
      },
    });
    expect(supabase.listEq).toHaveBeenCalledWith(
      "account_id",
      entitlement.account_id,
    );
    expect(supabase.listOrder).toHaveBeenCalledWith("updated_at", {
      ascending: false,
    });
  });

  it("inserts an active declared ranked-site declaration with normalized fields", async () => {
    const saved = declaration({
      id: "new-declaration",
      site_domain: "phoenix-roofing.example",
      niche_keyword: "Water Damage & Mold Repair",
      niche_normalized: "water_damage_and_mold_repair",
    });
    const supabase = createSupabaseMock({
      insertResult: { data: saved, error: null },
      listResult: {
        data: [
          declaration({ id: "existing-active", active: true, proof_state: "verified" }),
          saved,
        ],
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "POST",
      body: JSON.stringify({
        site_name: "Phoenix Roofing",
        site_url: "https://www.phoenix-roofing.example/services",
        city: "Phoenix",
        state: "az",
        cbsa_code: "38060",
        service: "Water Damage & Mold Repair",
        notes: "Currently ranking top three.",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      declaration: saved,
      unlock: {
        expand_conquer_unlocked: true,
        unlocked_strategy_ids: ["expand_conquer"],
        active_declaration_id: "existing-active",
      },
    });
    expect(supabase.insert).toHaveBeenCalledOnce();
    const [payload] = supabase.insert.mock.calls[0] as unknown as [
      Record<string, unknown>,
    ];
    expect(payload).toMatchObject({
      account_id: entitlement.account_id,
      created_by_user_id: user.id,
      updated_by_user_id: user.id,
      site_name: "Phoenix Roofing",
      site_url: "https://www.phoenix-roofing.example/services",
      site_domain: "phoenix-roofing.example",
      city: "Phoenix",
      state: "AZ",
      cbsa_code: "38060",
      niche_keyword: "Water Damage & Mold Repair",
      niche_normalized: "water_damage_and_mold_repair",
      proof_state: "declared",
      active: true,
      metadata: { notes: "Currently ranking top three." },
      verified_at: null,
      deactivated_at: null,
    });
    expect(payload.declared_at).toEqual(expect.any(String));
    expect(supabase.listEq).toHaveBeenCalledWith(
      "account_id",
      entitlement.account_id,
    );
  });

  it("returns 400 when POST lacks a valid domain", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "POST",
      body: JSON.stringify({
        site_name: "Phoenix Roofing",
        site_url: "not a domain",
        city: "Phoenix",
        state: "AZ",
        niche_keyword: "roofing",
      }),
    });

    const res = await POST(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message: "site_url or site_domain must contain a valid domain.",
    });
    expect(supabase.insert).not.toHaveBeenCalled();
  });

  it("deactivates by PATCH active=false and refreshes unlock state from remaining rows", async () => {
    const updated = declaration({
      id: "target-declaration",
      active: false,
      proof_state: "declared",
    });
    const remaining = [
      updated,
      declaration({ id: "other-active", active: true, proof_state: "verified" }),
    ];
    const supabase = createSupabaseMock({
      updateResult: { data: updated, error: null },
      listResult: { data: remaining, error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "PATCH",
      body: JSON.stringify({
        id: "target-declaration",
        active: false,
      }),
    });

    const res = await PATCH(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      declaration: updated,
      unlock: {
        expand_conquer_unlocked: true,
        active_declaration_id: "other-active",
      },
    });
    expect(supabase.update).toHaveBeenCalledOnce();
    const [payload] = supabase.update.mock.calls[0] as unknown as [
      Record<string, unknown>,
    ];
    expect(payload).toMatchObject({
      updated_by_user_id: user.id,
      active: false,
    });
    expect(payload.deactivated_at).toEqual(expect.any(String));
    expect(supabase.updateEqId).toHaveBeenCalledWith("id", "target-declaration");
    expect(supabase.updateEqAccount).toHaveBeenCalledWith(
      "account_id",
      entitlement.account_id,
    );
    expect(supabase.updateEqCreatedBy).toHaveBeenCalledWith(
      "created_by_user_id",
      user.id,
    );
  });

  it("does not clear stored site_url on domain-only PATCH", async () => {
    const updated = declaration({
      id: "target-declaration",
      site_domain: "new-domain.example",
    });
    const supabase = createSupabaseMock({
      updateResult: { data: updated, error: null },
      listResult: { data: [updated], error: null },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "PATCH",
      body: JSON.stringify({
        id: "target-declaration",
        site_domain: "new-domain.example",
      }),
    });

    const res = await PATCH(req as never);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toMatchObject({
      status: "success",
      declaration: updated,
    });
    const [payload] = supabase.update.mock.calls[0] as unknown as [
      Record<string, unknown>,
    ];
    expect(payload).toMatchObject({
      updated_by_user_id: user.id,
      site_domain: "new-domain.example",
    });
    expect(payload).not.toHaveProperty("site_url");
  });

  it("returns 409 when PATCH collides with an active declaration target", async () => {
    const supabase = createSupabaseMock({
      updateResult: {
        data: null,
        error: {
          message: "duplicate active ranked-site declaration",
          code: "23505",
        },
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "PATCH",
      body: JSON.stringify({
        id: "target-declaration",
        site_domain: "duplicate.example",
      }),
    });

    const res = await PATCH(req as never);
    const body = await res.json();

    expect(res.status).toBe(409);
    expect(body).toEqual({
      status: "error",
      message: "duplicate active ranked-site declaration",
    });
  });

  it("does not let this user route mark declarations verified", async () => {
    const supabase = createSupabaseMock();
    mocks.createClient.mockResolvedValue(supabase);

    const req = new Request("http://localhost/api/ranked-site-declarations", {
      method: "PATCH",
      body: JSON.stringify({
        id: "target-declaration",
        proof_state: "verified",
      }),
    });

    const res = await PATCH(req as never);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toEqual({
      status: "validation_error",
      message: "proof_state can only be declared from this route.",
    });
    expect(supabase.update).not.toHaveBeenCalled();
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string; code?: string } | null;
};

function createSupabaseMock(options: {
  listResult?: QueryResult;
  insertResult?: QueryResult;
  updateResult?: QueryResult;
} = {}) {
  const listResult = options.listResult ?? { data: [], error: null };
  const insertResult = options.insertResult ?? { data: null, error: null };
  const updateResult = options.updateResult ?? { data: null, error: null };

  const listOrder = vi.fn().mockResolvedValue(listResult);
  const listEq = vi.fn(() => ({ order: listOrder }));
  const listSelect = vi.fn(() => ({ eq: listEq }));

  const insertSingle = vi.fn().mockResolvedValue(insertResult);
  const insertSelect = vi.fn(() => ({ single: insertSingle }));
  const insert = vi.fn(() => ({ select: insertSelect }));

  const updateMaybeSingle = vi.fn().mockResolvedValue(updateResult);
  const updateSelect = vi.fn(() => ({ maybeSingle: updateMaybeSingle }));
  const updateEqCreatedBy = vi.fn(() => ({ select: updateSelect }));
  const updateEqAccount = vi.fn(() => ({ eq: updateEqCreatedBy }));
  const updateEqId = vi.fn(() => ({ eq: updateEqAccount }));
  const update = vi.fn(() => ({ eq: updateEqId }));

  return {
    listSelect,
    listEq,
    listOrder,
    insert,
    update,
    updateEqId,
    updateEqAccount,
    updateEqCreatedBy,
    from: vi.fn((table: string) => {
      if (table === "ranked_site_declarations") {
        return {
          select: listSelect,
          insert,
          update,
        };
      }
      throw new Error(`Unexpected table ${table}`);
    }),
  };
}

function declaration(overrides: Record<string, unknown> = {}) {
  return {
    id: "declaration-1",
    account_id: "33333333-3333-3333-3333-333333333333",
    created_by_user_id: "44444444-4444-4444-4444-444444444444",
    site_name: "Phoenix Roofing",
    site_url: "https://phoenix-roofing.example",
    site_domain: "phoenix-roofing.example",
    city: "Phoenix",
    state: "AZ",
    cbsa_code: "38060",
    niche_keyword: "roofing",
    niche_normalized: "roofing",
    proof_state: "declared",
    active: true,
    metadata: {},
    updated_at: "2026-07-05T12:00:00.000Z",
    ...overrides,
  };
}
