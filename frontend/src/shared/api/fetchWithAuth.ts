import {
  accessTokenNeedsRefresh,
  currentAccessToken,
  refreshAccessToken,
} from '@/shared/auth/tokenStore';

const publicTokenPaths = [
  '/api/accounts/login/',
  '/api/accounts/register/',
  '/api/accounts/verify-email/',
  '/api/accounts/resend-verification/',
  '/api/accounts/token/refresh/',
  '/api/accounts/token/revoke/',
];

function canRefresh(path: string) {
  return !publicTokenPaths.some((candidate) => path.includes(candidate));
}

function withBearer(headers: HeadersInit | undefined, token: string | null) {
  const next = new Headers(headers);
  if (token) next.set('Authorization', `Bearer ${token}`);
  return next;
}

export async function fetchWithAuth(url: string, path: string, init: RequestInit = {}) {
  if (canRefresh(path) && accessTokenNeedsRefresh()) await refreshAccessToken();
  const token = canRefresh(path) ? currentAccessToken() : null;
  let response = await fetch(url, {
    credentials: 'include',
    cache: 'no-store',
    ...init,
    headers: withBearer(init.headers, token),
  });

  if (response.status === 401 && canRefresh(path)) {
    const replacement = await refreshAccessToken();
    if (replacement) {
      response = await fetch(url, {
        credentials: 'include',
        cache: 'no-store',
        ...init,
        headers: withBearer(init.headers, replacement),
      });
    }
  }
  return response;
}
