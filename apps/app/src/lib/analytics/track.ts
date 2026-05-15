"use client";

type AnalyticsPayload = Record<string, unknown>;

interface PosthogWindow extends Window {
  posthog?: {
    capture: (event: string, payload?: AnalyticsPayload) => void;
  };
}

export function trackEvent(event: string, payload: AnalyticsPayload = {}): void {
  if (typeof window === "undefined") return;
  const sink = window as PosthogWindow;
  if (sink.posthog?.capture) {
    sink.posthog.capture(event, payload);
    return;
  }
  // Keep local visibility when analytics SDK is absent.
  console.info("[analytics] event=%s payload=%o", event, payload);
}
