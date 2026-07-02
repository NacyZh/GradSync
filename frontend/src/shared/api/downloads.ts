import { apiRequest } from './client';

export type DownloadDescriptor = {
  filename: string;
  deliveryMode: 'direct_response' | 'signed_url';
  url?: string;
  expiresAt?: string;
};

export function downloadDescriptor(path: string) {
  return apiRequest<DownloadDescriptor>(path, { method: 'POST' });
}
