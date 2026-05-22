import { beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";
import { createClient } from "@/lib/supabase/server";

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

const mockRpc = vi.fn();

function request(path: string) {
  return {
    nextUrl: new URL(`http://localhost:3001${path}`),
  };
}

describe("GET /api/billing/issues", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(createClient).mockResolvedValue({ rpc: mockRpc } as never);
    mockRpc.mockResolvedValue({ data: [], error: null });
  });

  it("loads billing issues through the admin-checked RPC", async () => {
    const res = await GET(request("/api/billing/issues?status=all&severity=error") as never);

    expect(res.status).toBe(200);
    expect(mockRpc).toHaveBeenCalledWith("list_billing_operation_events", {
      p_status: "all",
      p_severity: "error",
      p_limit: 50,
    });
  });

  it("returns forbidden when the RPC denies non-admin users", async () => {
    mockRpc.mockResolvedValueOnce({
      data: null,
      error: { code: "42501", message: "billing_admin_required" },
    });

    const res = await GET(request("/api/billing/issues") as never);
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body).toMatchObject({
      code: "billing_admin_required",
      message: "Admin access is required.",
    });
  });
});
