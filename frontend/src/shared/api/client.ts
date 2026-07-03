export type ApiError = {
  message: string;
  fields?: Record<string, string[]>;
};

function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() ?? null;
  }
  return null;
}

function addCsrfHeader(headers: HeadersInit, method: string): HeadersInit {
  const safeMethods = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];
  if (safeMethods.includes(method.toUpperCase())) {
    return headers;
  }
  const csrfToken = getCsrfToken();
  if (!csrfToken) {
    return headers;
  }
  return {
    ...(headers as Record<string, string>),
    'X-CSRFToken': csrfToken,
  };
}

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
  const method = init.method ?? 'GET';
  const isFormData = init.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : defaultHeaders),
    ...addCsrfHeader(init.headers ?? {}, method),
  };

  const response = await fetch(apiUrl(path), {
    credentials: 'include',
    ...init,
    method,
    headers,
  });

  if (response.status === 401) {
    // Session expired or not authenticated — signal the app to show login.
    window.dispatchEvent(new CustomEvent('gradsync:auth-required'));
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as Partial<ApiError>;
    const fieldMessages = payload.fields
      ? Object.entries(payload.fields)
          .flatMap(([field, messages]) => messages.map((message) => `${field}: ${message}`))
          .join('; ')
      : '';
    throw {
      message: payload.message ?? (fieldMessages || `Request failed with ${response.status}`),
      fields: payload.fields,
    };
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
