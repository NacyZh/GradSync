import { apiRequest, apiUrl } from './client';
import { fetchWithAuth } from './fetchWithAuth';

export type DownloadDescriptor = {
  filename: string;
  deliveryMode: 'direct_response' | 'signed_url';
  url?: string;
  expiresAt?: string;
};

export function downloadDescriptor(path: string) {
  return apiRequest<DownloadDescriptor>(path, { method: 'POST' });
}

function filenameFromContentDisposition(header: string | null): string | undefined {
  if (!header) return undefined;
  const encodedMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    return decodeURIComponent(encodedMatch[1].replace(/"/g, '').trim());
  }
  const plainMatch = header.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1]?.trim();
}

async function errorMessageFromResponse(response: Response) {
  const payload = await response.json().catch(() => ({})) as Partial<{ detail: string; message: string; fields: Record<string, string[]> }>;
  if (payload.message) return payload.message;
  if (payload.detail) return payload.detail;
  if (payload.fields) {
    return Object.entries(payload.fields)
      .flatMap(([field, messages]) => messages.map((message) => `${field}: ${message}`))
      .join('; ');
  }
  return `Request failed with ${response.status}`;
}

export async function downloadFile(path: string, fallbackFilename = 'download.pdf', method = 'GET'): Promise<DownloadDescriptor> {
  const response = await fetchWithAuth(apiUrl(path), path, {
    method,
  });

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('gradsync:auth-required'));
  }

  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }

  const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition')) ?? fallbackFilename;
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = 'noopener';
  anchor.style.display = 'none';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);

  return {
    filename,
    deliveryMode: 'direct_response',
  };
}

export async function fetchDownloadBlobUrl(path: string): Promise<string> {
  const response = await fetchWithAuth(apiUrl(path), path, {
    method: 'GET',
  });

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('gradsync:auth-required'));
  }

  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }

  return URL.createObjectURL(await response.blob());
}
