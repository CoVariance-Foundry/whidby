import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";

export async function GET() {
  try {
    const upstream = await proxyStrategyResponse("/api/strategies", {
      method: "GET",
    });
    return proxyStrategyJsonResponse(upstream);
  } catch (err) {
    return strategyUpstreamUnavailable(
      err,
      "Strategy catalog service is unavailable.",
    );
  }
}
