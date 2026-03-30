import { getSessionId, getStoredUTMParams } from './utm';

type EventData = Record<string, unknown>;

let pageLoadTime = 0;
let sawPricing = false;

export function initAnalytics() {
  pageLoadTime = Date.now();
}

export function markPricingSeen() {
  sawPricing = true;
}

export function hasSawPricing(): boolean {
  return sawPricing;
}

export async function trackEvent(eventName: string, eventData: EventData = {}) {
  const utm = getStoredUTMParams();
  const sessionId = getSessionId();

  const payload = {
    event_name: eventName,
    event_data: eventData,
    page_url: window.location.href,
    referrer: document.referrer || null,
    utm_source: utm.utm_source || null,
    utm_medium: utm.utm_medium || null,
    utm_campaign: utm.utm_campaign || null,
    utm_term: utm.utm_term || null,
    utm_content: utm.utm_content || null,
    session_id: sessionId,
    user_agent: navigator.userAgent,
    screen_width: window.innerWidth,
  };

  try {
    await fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    // Silently fail — analytics should never break the UI
  }
}

export function trackPageView() {
  trackEvent('page_view');
}

export function trackCTAClick(ctaName: string, ctaLocation: string) {
  trackEvent('cta_click', { cta_name: ctaName, cta_location: ctaLocation });
}

export function trackSectionView(sectionId: string) {
  if (sectionId === 'pricing') markPricingSeen();
  const timeOnPage = Math.round((Date.now() - pageLoadTime) / 1000);
  trackEvent('section_view', { section_id: sectionId, time_on_page: timeOnPage });
}

export function trackScrollDepth(depthPercent: number) {
  const timeToReach = Math.round((Date.now() - pageLoadTime) / 1000);
  trackEvent('scroll_depth', { depth_percent: depthPercent, time_to_reach: timeToReach });
}

export function trackWaitlistSignup(email: string, source: string, portfolioSize: string) {
  const emailHash = btoa(email).slice(0, 12);
  trackEvent('waitlist_signup', {
    email_hash: emailHash,
    signup_source: source,
    portfolio_size: portfolioSize,
    saw_pricing: hasSawPricing(),
  });
}
