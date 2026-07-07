import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadDescriptor, downloadFile, fetchDownloadBlobUrl } from '../../shared/api/downloads';

export type PaperRecord = {
  id: string;
  projectId: string;
  title: string;
  canonicalTitle?: string;
  titleSource?: 'embedded_metadata' | 'first_page_visible_text' | 'legacy' | string;
  titleConfidence?: 'high' | 'medium' | 'low' | 'failed' | string;
  downloadAvailable?: boolean;
  viewerAvailable?: boolean;
  actionCapabilities?: {
    canRename: boolean;
    canDelete: boolean;
    canDownload: boolean;
    canView: boolean;
  };
  defaultDownloadFilename?: string;
  migratedFromLegacyScope?: boolean;
  sharedAccessStartedAt?: string;
  createdAt?: string;
  authors: string[];
  venue?: string;
  publicationYear?: number;
  doi?: string;
  abstract?: string;
  tags?: string[];
  keywords?: string[];
  visibility: 'project_members' | 'group_wide';
  checksumSha256?: string;
  uploadedFileId?: string;
  sourcePathLabel?: string;
  status: string;
  attachments?: { id: string; filename: string; relativePath?: string; checksumSha256: string; status: string }[];
};

export type PaperSearchFilters = {
  query?: string;
  author?: string;
  year?: string;
  keyword?: string;
};

export type PaperUploadPolicy = {
  category: 'paper';
  maxSizeBytes: number;
  displayLabel: string;
  allowedExtensions: string[];
  contentTypes: string[];
};

export type PaperRenamePayload = {
  newTitle: string;
  reason?: string;
};

export type PaperDeletePayload = {
  reason?: string;
};

export type PaperDownloadDescriptor = {
  filename: string;
  deliveryMode: 'direct_response' | 'signed_url';
  url?: string;
  expiresAt?: string;
};

export type PaperImportBatch = {
  id: string;
  projectId: string;
  status: string;
  sourcePathLabel?: string;
  totalItems: number;
  acceptedCount: number;
  duplicateCount: number;
  errorCount: number;
  results: Array<{ status: string; duplicateReason?: string; duplicateOfPaperId?: string; message?: string; paper?: PaperRecord | Record<string, unknown> }>;
};

export type PaperImportJob = {
  id: string;
  status:
    | 'uploading'
    | 'validating'
    | 'extracting_title'
    | 'checking_duplicate'
    | 'accepted'
    | 'duplicate'
    | 'maintainer_review'
    | 'rejected'
    | 'failed';
  requestedBy: string;
  userMessage?: string;
  acceptedPaper?: PaperRecord | null;
  duplicatePaper?: PaperRecord | null;
  extraction?: {
    source: 'embedded_metadata' | 'first_page_visible_text' | string;
    extractedTitle?: string;
    confidence?: string;
    failureReason?: string;
  } | null;
  duplicateDetection?: {
    decision: string;
    matchBasis: string;
    candidatePaperId?: string;
    similarityScore?: number;
    reviewStatus: string;
  } | null;
  failureReason?: string;
  createdAt?: string;
  updatedAt?: string;
  completedAt?: string;
};

export type PaperCreatePayload = {
  title: string;
  authors: string[];
  venue?: string;
  publicationYear?: number;
  doi?: string;
  tags?: string[];
  sourcePathLabel?: string;
};

export type PaperUploadPayload = {
  file: File;
  title: string;
  authors: string;
  venue?: string;
  publicationYear?: string;
  keywords?: string;
  abstract?: string;
  visibility: 'project_members' | 'group_wide';
};

export function listPapers(projectId: number, query = '', visibility = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (visibility) params.set('visibility', visibility);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: PaperRecord[] }>(`/api/projects/${projectId}/papers/${suffix}`);
}

export function listSharedPapers(filters: PaperSearchFilters = {}) {
  const params = new URLSearchParams();
  if (filters.query) params.set('q', filters.query);
  if (filters.author) params.set('author', filters.author);
  if (filters.year) params.set('year', filters.year);
  if (filters.keyword) params.set('keyword', filters.keyword);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ count: number; results: PaperRecord[] }>(`/api/library/papers/${suffix}`);
}

export function getSharedPaper(paperId: string) {
  return apiRequest<PaperRecord>(`/api/library/papers/${paperId}/`);
}

export function getPaperUploadPolicy() {
  return apiRequest<PaperUploadPolicy>('/api/library/papers/upload-policy/');
}

export function renameSharedPaper(paperId: string, payload: PaperRenamePayload) {
  return apiRequest<PaperRecord>(`/api/library/papers/${paperId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteSharedPaper(paperId: string, payload: PaperDeletePayload = {}) {
  return apiRequest<void>(`/api/library/papers/${paperId}/`, {
    method: 'DELETE',
    body: JSON.stringify(payload),
  });
}

export function createPaper(projectId: number, payload: PaperCreatePayload) {
  return apiRequest<PaperRecord>(`/api/projects/${projectId}/papers/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function uploadPaper(projectId: number, payload: PaperUploadPayload) {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('title', payload.title);
  formData.append('authors', payload.authors);
  formData.append('visibility', payload.visibility);
  if (payload.venue) formData.append('venue', payload.venue);
  if (payload.publicationYear) formData.append('publicationYear', payload.publicationYear);
  if (payload.keywords) formData.append('keywords', payload.keywords);
  if (payload.abstract) formData.append('abstract', payload.abstract);
  return apiRequest<PaperRecord>(`/api/projects/${projectId}/papers/`, {
    method: 'POST',
    body: formData,
  });
}

export function importSharedPaperPdf(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return apiRequest<PaperImportJob>('/api/library/papers/', {
    method: 'POST',
    body: formData,
  });
}

export function getPaperImportJob(importJobId: string) {
  return apiRequest<PaperImportJob>(`/api/library/paper-imports/${importJobId}/`);
}

export type PaperImportReviewDecision = 'confirm_duplicate' | 'confirm_distinct';

export function reviewPaperImport(importJobId: string, decision: PaperImportReviewDecision, note = '') {
  return apiRequest<PaperImportJob>(`/api/library/paper-imports/${importJobId}/review/`, {
    method: 'POST',
    body: JSON.stringify({ decision, note }),
  });
}

export type PaperImportPayload = {
  items: PaperCreatePayload[];
  sourcePathLabel: string;
};

export function stagePaperImport(projectId: number, items: PaperCreatePayload[], sourcePathLabel = 'local-library') {
  return apiRequest<PaperImportBatch>(`/api/projects/${projectId}/papers/imports/`, {
    method: 'POST',
    body: JSON.stringify({ sourceType: 'mixed_local', sourcePathLabel, items }),
  });
}

export function downloadPaper(projectId: number, paperId: string) {
  return downloadDescriptor(`/api/projects/${projectId}/papers/${paperId}/download/`);
}

export function downloadSharedPaper(paperId: string, fallbackFilename?: string) {
  return downloadFile(`/api/library/papers/${paperId}/download/`, fallbackFilename);
}

export function downloadSharedPaperFile(paperId: string) {
  return downloadFile(`/api/library/papers/${paperId}/download/`);
}

export function previewSharedPaperFile(paperId: string) {
  return fetchDownloadBlobUrl(`/api/library/papers/${paperId}/download/`);
}

export function usePapers(projectId: number, query: string, visibility = '') {
  return useQuery({
    queryKey: ['papers', projectId, query, visibility],
    queryFn: () => listPapers(projectId, query, visibility),
    enabled: Boolean(projectId),
  });
}

export function useSharedPapers(filters: PaperSearchFilters) {
  return useQuery({
    queryKey: ['shared-papers', filters],
    queryFn: () => listSharedPapers(filters),
  });
}

export function useSharedPaperDetail(paperId?: string) {
  return useQuery({
    queryKey: ['shared-paper', paperId],
    queryFn: () => getSharedPaper(paperId ?? ''),
    enabled: Boolean(paperId),
  });
}

export function usePaperUploadPolicy() {
  return useQuery({
    queryKey: ['paper-upload-policy'],
    queryFn: getPaperUploadPolicy,
  });
}

export function useRenameSharedPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, payload }: { paperId: string; payload: PaperRenamePayload }) =>
      renameSharedPaper(paperId, payload),
    onSuccess: (paper) => {
      queryClient.setQueryData(['shared-paper', paper.id], paper);
      queryClient.setQueriesData<{ count: number; results: PaperRecord[] }>(
        { queryKey: ['shared-papers'] },
        (current) => {
          if (!current) return current;
          return {
            ...current,
            results: current.results.map((item) => (item.id === paper.id ? paper : item)),
          };
        },
      );
      queryClient.invalidateQueries({ queryKey: ['shared-papers'] });
      queryClient.invalidateQueries({ queryKey: ['shared-paper', paper.id] });
    },
  });
}

export function useDeleteSharedPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, payload }: { paperId: string; payload?: PaperDeletePayload }) =>
      deleteSharedPaper(paperId, payload),
    onSuccess: (_result, variables) => {
      queryClient.removeQueries({ queryKey: ['shared-paper', variables.paperId] });
      queryClient.setQueriesData<{ count: number; results: PaperRecord[] }>(
        { queryKey: ['shared-papers'] },
        (current) => {
          if (!current) return current;
          return {
            ...current,
            count: Math.max(0, current.count - current.results.filter((item) => item.id === variables.paperId).length),
            results: current.results.filter((item) => item.id !== variables.paperId),
          };
        },
      );
      queryClient.invalidateQueries({ queryKey: ['shared-papers'] });
    },
  });
}

export function useCreatePaper(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PaperCreatePayload) => createPaper(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['papers', projectId] }),
  });
}

export function usePaperUpload(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PaperUploadPayload) => uploadPaper(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['papers', projectId] }),
  });
}

export function useSharedPaperPdfImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importSharedPaperPdf(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shared-papers'] }),
  });
}

export function usePaperImportReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      importJobId,
      decision,
      note,
    }: {
      importJobId: string;
      decision: PaperImportReviewDecision;
      note?: string;
    }) => reviewPaperImport(importJobId, decision, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shared-papers'] }),
  });
}

export function usePaperImport(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ items, sourcePathLabel }: PaperImportPayload) =>
      stagePaperImport(projectId, items, sourcePathLabel),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['papers', projectId] }),
  });
}
