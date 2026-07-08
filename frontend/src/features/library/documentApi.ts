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
  actionCapabilities?: {
    canView: boolean;
    canDownload: boolean;
    canRename: boolean;
    canDelete: boolean;
    canUploadGroupWide: boolean;
  };
};

export type DocumentUploadPayload = {
  file: File;
  title?: string;
  categoryId: string;
  description?: string;
  visibility?: 'project_members' | 'group_wide';
};

export type DocumentRenamePayload = {
  newTitle: string;
  reason?: string;
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
  formData.append('categoryId', payload.categoryId);
  if (payload.title?.trim()) formData.append('title', payload.title.trim());
  if (payload.description) formData.append('description', payload.description);
  if (payload.visibility) formData.append('visibility', payload.visibility);
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents`, {
    method: 'POST',
    body: formData,
  });
}

export function retrieveDocument(projectId: number, documentId: string) {
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents/${documentId}`);
}

export function renameDocument(projectId: number, documentId: string, payload: DocumentRenamePayload) {
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents/${documentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteDocument(projectId: number, documentId: string) {
  return apiRequest<void>(`/api/projects/${projectId}/documents/${documentId}`, {
    method: 'DELETE',
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

export function useDocument(projectId: number, documentId?: string) {
  return useQuery({
    queryKey: ['document', projectId, documentId],
    queryFn: () => retrieveDocument(projectId, documentId as string),
    enabled: Boolean(projectId && documentId),
  });
}

export function useDocumentUpload(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentUploadPayload) => uploadDocument(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', projectId] }),
  });
}

export function useRenameDocument(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, payload }: { documentId: string; payload: DocumentRenamePayload }) =>
      renameDocument(projectId, documentId, payload),
    onSuccess: (document) => {
      queryClient.setQueryData(['document', projectId, document.id], document);
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] });
    },
  });
}

export function useDeleteDocument(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(projectId, documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', projectId] }),
  });
}
