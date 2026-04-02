const UTM_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'] as const;
const SESSION_KEY = 'rr_session_id';
const UTM_KEY = 'rr_utm';

export type UTMParams = {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
};

export function getSessionId(): string {
  if (typeof window === 'undefined') return '';
  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

export function captureUTMParams(): UTMParams {
  if (typeof window === 'undefined') return {};

  const url = new URL(window.location.href);
  const params: UTMParams = {};
  let hasNew = false;

  for (const key of UTM_PARAMS) {
    const value = url.searchParams.get(key);
    if (value) {
      params[key] = value;
      hasNew = true;
    }
  }

  if (hasNew) {
    sessionStorage.setItem(UTM_KEY, JSON.stringify(params));
    return params;
  }

  const stored = sessionStorage.getItem(UTM_KEY);
  return stored ? JSON.parse(stored) : {};
}

export function getStoredUTMParams(): UTMParams {
  if (typeof window === 'undefined') return {};
  const stored = sessionStorage.getItem(UTM_KEY);
  return stored ? JSON.parse(stored) : {};
}
