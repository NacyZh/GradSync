import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadDescriptor } from '../../shared/api/downloads';

export type PaperRecord = {
  id: string;
  projectId: string;
  title: string;
  authors: string[];
  venue?: string;
  publicationYear?: number;
  doi?: string;
  tags?: string[];
  status: string;
  attachments?: { id: string; filename: string; checksumSha256: string; status: string }[];
};

export type PaperImportBatch = {
  id: string;
  projectId: string;
  status: string;
  totalItems: number;
  acceptedCount: number;
  duplicateCount: number;
  errorCount: number;
  results: Array<{ status: string; duplicateReason?: string; duplicateOfPaperId?: string; message?: string; paper?: PaperRecord | Record<string, unknown> }>;
};

export type PaperCreatePayload = {
  title: string;
  authors: string[];
  venue?: string;
  publicationYear?: number;
  doi?: string;
  tags?: string[];
};

export function listPapers(projectId: number, query = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: PaperRecord[] }>(`/api/projects/${projectId}/papers/${suffix}`);
}

export function createPaper(projectId: number, payload: PaperCreatePayload) {
  return apiRequest<PaperRecord>(`/api/projects/${projectId}/papers/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function stagePaperImport(projectId: number, items: PaperCreatePayload[]) {
  return apiRequest<PaperImportBatch>(`/api/projects/${projectId}/papers/imports/`, {
    method: 'POST',
    body: JSON.stringify({ sourceType: 'mixed', items }),
  });
}

export function downloadPaper(projectId: number, paperId: string) {
  return downloadDescriptor(`/api/projects/${projectId}/papers/${paperId}/download/`);
}

export function usePapers(projectId: number, query: string) {
  return useQuery({
    queryKey: ['papers', projectId, query],
    queryFn: () => listPapers(projectId, query),
    enabled: Boolean(projectId),
  });
}

export function useCreatePaper(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PaperCreatePayload) => createPaper(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['papers', projectId] }),
  });
}

export function usePaperImport(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: PaperCreatePayload[]) => stagePaperImport(projectId, items),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['papers', projectId] }),
  });
}
