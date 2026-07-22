type AccessTokenPayload = {
  accessToken?: string;
  accessTokenExpiresAt?: string;
};

let accessToken: string | null = null;
let accessTokenExpiresAt = 0;
let refreshPromise: Promise<string | null> | null = null;

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

function csrfToken() {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function setAccessToken(payload: AccessTokenPayload) {
  accessToken = payload.accessToken ?? null;
  accessTokenExpiresAt = payload.accessTokenExpiresAt
    ? new Date(payload.accessTokenExpiresAt).getTime()
    : 0;
}

export function clearAccessToken() {
  accessToken = null;
  accessTokenExpiresAt = 0;
}

export function currentAccessToken() {
  return accessToken;
}

export function accessTokenNeedsRefresh() {
  return Boolean(accessToken && accessTokenExpiresAt && accessTokenExpiresAt <= Date.now() + 30_000);
}

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const csrf = csrfToken();
    const response = await fetch(`${apiBaseUrl}/api/accounts/token/refresh/`, {
      method: 'POST',
      credentials: 'include',
      headers: csrf ? { 'X-CSRFToken': csrf } : undefined,
      cache: 'no-store',
    });
    if (!response.ok) {
      clearAccessToken();
      return null;
    }
    const payload = (await response.json()) as AccessTokenPayload;
    setAccessToken(payload);
    return accessToken;
  })().catch(() => {
    clearAccessToken();
    return null;
  }).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function restoreAccessToken() {
  if (accessToken && !accessTokenNeedsRefresh()) return accessToken;
  return refreshAccessToken();
}
