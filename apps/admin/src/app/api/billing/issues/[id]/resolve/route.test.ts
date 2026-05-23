import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";
import { createClient } from "@/lib/supabase/server";

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

const mockRpc = vi.fn();

describe("POST /api/billing/issues/[id]/resolve", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(createClient).mockResolvedValue({ rpc: mockRpc } as never);
    mockRpc.mockResolvedValue({ data: null, error: null });
  });

  it("resolves a billing issue through the admin-checked RPC", async () => {
    const res = await POST(new Request("http://localhost") as never, {
      params: Promise.resolve({ id: "11111111-1111-1111-1111-111111111111" }),
    });

    expect(res.status).toBe(200);
    expect(mockRpc).toHaveBeenCalledWith("resolve_billing_operation_event", {
      p_event_id: "11111111-1111-1111-1111-111111111111",
    });
  });

  it("returns forbidden when the RPC denies non-admin users", async () => {
    mockRpc.mockResolvedValueOnce({
      data: null,
      error: { code: "42501", message: "billing_admin_required" },
    });

    const res = await POST(new Request("http://localhost") as never, {
      params: Promise.resolve({ id: "11111111-1111-1111-1111-111111111111" }),
    });
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body.code).toBe("billing_admin_required");
  });

  it("returns not found when the RPC cannot resolve the event id", async () => {
    mockRpc.mockResolvedValueOnce({
      data: null,
      error: { code: "P0002", message: "billing_event_not_found" },
    });

    const res = await POST(new Request("http://localhost") as never, {
      params: Promise.resolve({ id: "11111111-1111-1111-1111-111111111111" }),
    });
    const body = await res.json();

    expect(res.status).toBe(404);
    expect(body.code).toBe("billing_issue_not_found");
  });
});
