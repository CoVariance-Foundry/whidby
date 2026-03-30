'use client';

import { getSessionId, captureUTMParams } from './utm';

interface EventPayload {
  event_name: string;
  event_data?: Record<string, unknown>;
  page_url?: string;
  referrer?: string;
}

let pageLoadTime: number | null = null;

export function initAnalytics() {
  pageLoadTime = Date.now();
}

function getTimeSinceLoad(): number {
  if (!pageLoadTime) return 0;
  return Math.round((Date.now() - pageLoadTime) / 1000);
}

export async function trackEvent(name: string, data?: Record<string, unknown>) {
  try {
    const utm = captureUTMParams();
    const sessionId = getSessionId();

    const payload: EventPayload = {
      event_name: name,
      event_data: data || {},
      page_url: window.location.href,
      referrer: document.referrer || undefined,
    };

    await fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...payload,
        ...utm,
        session_id: sessionId,
        user_agent: navigator.userAgent,
        screen_width: window.innerWidth,
      }),
    });
  } catch {
    // Silently fail - analytics should never break the app
  }
}

export function trackPageView() {
  trackEvent('page_view');
}

export function trackCTAClick(ctaName: string, ctaLocation: string) {
  trackEvent('cta_click', {
    cta_name: ctaName,
    cta_location: ctaLocation,
    time_on_page: getTimeSinceLoad(),
  });
}

export function trackSectionView(sectionId: string) {
  trackEvent('section_view', {
    section_id: sectionId,
    time_on_page: getTimeSinceLoad(),
  });
}

export function trackScrollDepth(percent: number) {
  trackEvent('scroll_depth', {
    depth_percent: percent,
    time_to_reach: getTimeSinceLoad(),
  });
}

export function trackWaitlistSignup(email: string, sourceSection: string) {
  trackEvent('waitlist_signup', {
    email_domain: email.split('@')[1],
    source_section: sourceSection,
    time_on_page: getTimeSinceLoad(),
  });
}
