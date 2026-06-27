export type ApiError = {
  message: string;
  fields?: Record<string, string[]>;
};

const defaultHeaders = {
  'Content-Type': 'application/json',
};

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${apiBaseUrl}${path}`;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    credentials: 'include',
    ...init,
    headers: {
      ...defaultHeaders,
      ...init.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as Partial<ApiError>;
    throw { message: payload.message ?? `Request failed with ${response.status}`, fields: payload.fields };
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
