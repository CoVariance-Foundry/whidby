import { beforeEach, describe, expect, it, vi } from "vitest";
import ReportDetailPage from "./page";
import { notFound } from "next/navigation";

const mocks = vi.hoisted(() => ({
  headersGet: vi.fn(),
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => ({
    get: mocks.headersGet,
  })),
}));

vi.mock("next/navigation", () => ({
  notFound: mocks.notFound,
}));

beforeEach(() => {
  delete process.env.WIDBY_APP_BASE_URL;
  delete process.env.NEXT_PUBLIC_APP_URL;
  delete process.env.NEXT_PUBLIC_SITE_URL;
  delete process.env.VERCEL_URL;
  mocks.headersGet.mockImplementation((name: string) => {
    const values: Record<string, string> = {
      host: "preview.whidby.test",
      cookie: "sb-access-token=abc",
    };
    return values[name] ?? null;
  });
  global.fetch = vi.fn();
  vi.clearAllMocks();
});

describe("ReportDetailPage", () => {
  it("does not fetch a relative report URL for non-local request hosts", async () => {
    await expect(
      ReportDetailPage({
        params: Promise.resolve({ reportId: "report-1" }),
      }),
    ).rejects.toThrow("NEXT_NOT_FOUND");

    expect(global.fetch).not.toHaveBeenCalled();
    expect(notFound).toHaveBeenCalledOnce();
  });
});
