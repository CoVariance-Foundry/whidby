'use client';

const UTM_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'] as const;
const SESSION_KEY = 'rr_session_id';
const UTM_KEY = 'rr_utm';

export interface UTMData {
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_term: string | null;
  utm_content: string | null;
}

export function getSessionId(): string {
  if (typeof window === 'undefined') return '';
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function captureUTMParams(): UTMData {
  if (typeof window === 'undefined') {
    return { utm_source: null, utm_medium: null, utm_campaign: null, utm_term: null, utm_content: null };
  }

  const stored = sessionStorage.getItem(UTM_KEY);
  if (stored) {
    return JSON.parse(stored);
  }

  const params = new URLSearchParams(window.location.search);
  const utm: UTMData = {
    utm_source: null,
    utm_medium: null,
    utm_campaign: null,
    utm_term: null,
    utm_content: null,
  };

  let hasUtm = false;
  for (const key of UTM_PARAMS) {
    const val = params.get(key);
    if (val) {
      utm[key] = val;
      hasUtm = true;
    }
  }

  if (hasUtm) {
    sessionStorage.setItem(UTM_KEY, JSON.stringify(utm));
  }

  return utm;
}
