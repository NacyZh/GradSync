import { readFileSync } from 'node:fs';
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchWithAuth } from '../../src/shared/api/fetchWithAuth';
import {
  clearAccessToken,
  currentAccessToken,
  setAccessToken,
} from '../../src/shared/auth/tokenStore';

afterEach(() => {
  clearAccessToken();
  vi.restoreAllMocks();
  document.cookie = 'csrftoken=; Max-Age=0; path=/';
});

describe('token authentication client', () => {
  it('keeps access tokens in memory and sends Bearer authentication', async () => {
    setAccessToken({
      accessToken: 'memory-token',
      accessTokenExpiresAt: new Date(Date.now() + 60_000).toISOString(),
    });
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue(new Response('{}'));

    await fetchWithAuth('/api/projects/', '/api/projects/');

    const headers = new Headers(fetchSpy.mock.calls[0][1]?.headers);
    expect(headers.get('Authorization')).toBe('Bearer memory-token');
    expect(window.localStorage.getItem('accessToken')).toBeNull();
    expect(window.localStorage.getItem('refreshToken')).toBeNull();
  });

  it('refreshes once and replays a rejected request with the replacement token', async () => {
    document.cookie = 'csrftoken=csrf-value; path=/';
    setAccessToken({
      accessToken: 'expired-token',
      accessTokenExpiresAt: new Date(Date.now() + 60_000).toISOString(),
    });
    const fetchSpy = vi.spyOn(window, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/token/refresh/')) {
        return new Response(JSON.stringify({
          accessToken: 'replacement-token',
          accessTokenExpiresAt: new Date(Date.now() + 60_000).toISOString(),
        }), { status: 200 });
      }
      const authorization = new Headers(fetchSpy.mock.calls.at(-1)?.[1]?.headers).get('Authorization');
      return new Response('{}', { status: authorization === 'Bearer replacement-token' ? 200 : 401 });
    });

    const response = await fetchWithAuth('/api/projects/', '/api/projects/');

    expect(response.status).toBe(200);
    expect(currentAccessToken()).toBe('replacement-token');
    expect(fetchSpy.mock.calls.filter(([url]) => String(url).includes('/token/refresh/'))).toHaveLength(1);
    const replayHeaders = new Headers(fetchSpy.mock.calls.at(-1)?.[1]?.headers);
    expect(replayHeaders.get('Authorization')).toBe('Bearer replacement-token');
  });

  it('does not attach stale credentials to login or registration endpoints', async () => {
    setAccessToken({
      accessToken: 'stale-token',
      accessTokenExpiresAt: new Date(Date.now() + 60_000).toISOString(),
    });
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue(new Response('{}'));

    await fetchWithAuth('/api/accounts/login/', '/api/accounts/login/', { method: 'POST' });

    const headers = new Headers(fetchSpy.mock.calls[0][1]?.headers);
    expect(headers.has('Authorization')).toBe(false);
  });
});

describe('Cache API offline boundary', () => {
  it('pre-caches only the app shell and bypasses authenticated business data', () => {
    const serviceWorker = readFileSync(path.resolve(process.cwd(), 'public/sw.js'), 'utf8');

    expect(serviceWorker).toContain("'/asset-manifest.json'");
    expect(serviceWorker).toContain('Object.values(manifest)');
    expect(serviceWorker).toContain("url.pathname.startsWith('/api/')");
    expect(serviceWorker).toContain("url.pathname.startsWith('/media/')");
    expect(serviceWorker).toContain("request.headers.has('Authorization')");
    expect(serviceWorker).toContain("request.method !== 'GET'");
    expect(serviceWorker).toContain("request.mode === 'navigate'");
    expect(serviceWorker).toContain("url.pathname.startsWith('/assets/')");
  });
});
