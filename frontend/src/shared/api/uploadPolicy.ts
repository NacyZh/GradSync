import { useQuery } from '@tanstack/react-query';

import { apiRequest } from './client';

export type UploadCategory = 'paper' | 'code' | 'document' | 'writing' | 'feedback';

export type UploadPolicy = {
  category: UploadCategory;
  maxSizeBytes: number;
  displayLabel: string;
  allowedExtensions: string[];
  contentTypes: string[];
};

export async function getUploadPolicy(category: UploadCategory) {
  const policy = await apiRequest<UploadPolicy>(`/api/upload-policies/${category}/`);
  if (
    policy.category !== category
    || !Number.isFinite(policy.maxSizeBytes)
    || policy.maxSizeBytes <= 0
    || !policy.displayLabel
    || !Array.isArray(policy.allowedExtensions)
  ) {
    throw new Error('Upload policy response is invalid.');
  }
  return policy;
}

export function useUploadPolicy(category: UploadCategory) {
  return useQuery({
    queryKey: ['upload-policy', category],
    queryFn: () => getUploadPolicy(category),
    staleTime: 5 * 60_000,
  });
}

export function uploadSizeError(file: File | undefined, policy: UploadPolicy | undefined) {
  if (!file || !policy || file.size <= policy.maxSizeBytes) return '';
  return `${file.name} exceeds the ${policy.displayLabel} upload size limit.`;
}
