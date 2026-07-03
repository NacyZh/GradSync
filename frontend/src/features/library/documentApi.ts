import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import type { DownloadDescriptor } from '../../shared/api/downloads';

export type DocumentCategory = {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived';
};

export type DocumentRecord = {
  id: string;
  projectId: string;
  visibility: 'project_members' | 'group_wide';
  uploaderId: string;
  createdAt: string;
  categoryId: string;
  categoryName?: string;
  title: string;
  description?: string;
  documentFileId?: string;
  checksumSha256?: string;
  status: string;
};

export type DocumentUploadPayload = {
  file: File;
  title: string;
  categoryId: string;
  description?: string;
  visibility: 'project_members' | 'group_wide';
};

export function listDocumentCategories() {
  return apiRequest<DocumentCategory[]>('/api/document-categories');
}

export function createDocumentCategory(payload: { name: string; description?: string }) {
  return apiRequest<DocumentCategory>('/api/document-categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listDocuments(projectId: number, query = '', categoryId = '', visibility = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (categoryId) params.set('categoryId', categoryId);
  if (visibility) params.set('visibility', visibility);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: DocumentRecord[] }>(`/api/projects/${projectId}/documents${suffix}`);
}

export function uploadDocument(projectId: number, payload: DocumentUploadPayload) {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('title', payload.title);
  formData.append('categoryId', payload.categoryId);
  formData.append('visibility', payload.visibility);
  if (payload.description) formData.append('description', payload.description);
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents`, {
    method: 'POST',
    body: formData,
  });
}

export function downloadDocument(documentId: string) {
  return apiRequest<DownloadDescriptor>(`/api/documents/${documentId}/download`);
}

export function useDocumentCategories() {
  return useQuery({
    queryKey: ['documentCategories'],
    queryFn: listDocumentCategories,
  });
}

export function useDocuments(projectId: number, query: string, categoryId: string, visibility: string) {
  return useQuery({
    queryKey: ['documents', projectId, query, categoryId, visibility],
    queryFn: () => listDocuments(projectId, query, categoryId, visibility),
    enabled: Boolean(projectId),
  });
}

export function useDocumentUpload(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentUploadPayload) => uploadDocument(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', projectId] }),
  });
}
