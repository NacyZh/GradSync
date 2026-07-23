import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadFile } from '../../shared/api/downloads';

export type DocumentCategory = {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived';
};

export type DocumentRecord = {
  id: string;
  projectId: string;
  boundaryType?: 'standalone_shared' | 'project_material';
  sourceProject?: { id: string; title: string } | null;
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

export function listSharedDocuments(query = '', categoryId = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (categoryId) params.set('categoryId', categoryId);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ count: number; results: DocumentRecord[] }>(`/api/library/documents/${suffix}`);
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

export function uploadSharedDocument(payload: DocumentUploadPayload) {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('categoryId', payload.categoryId);
  if (payload.title?.trim()) formData.append('title', payload.title.trim());
  if (payload.description) formData.append('description', payload.description);
  return apiRequest<DocumentRecord>('/api/library/documents/', {
    method: 'POST',
    body: formData,
  });
}

export function retrieveDocument(projectId: number, documentId: string) {
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents/${documentId}`);
}

export function retrieveSharedDocument(documentId: string) {
  return apiRequest<DocumentRecord>(`/api/library/documents/${documentId}/`);
}

export function renameDocument(projectId: number, documentId: string, payload: DocumentRenamePayload) {
  return apiRequest<DocumentRecord>(`/api/projects/${projectId}/documents/${documentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function renameSharedDocument(documentId: string, payload: DocumentRenamePayload) {
  return apiRequest<DocumentRecord>(`/api/library/documents/${documentId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteDocument(projectId: number, documentId: string) {
  return apiRequest<void>(`/api/projects/${projectId}/documents/${documentId}`, {
    method: 'DELETE',
  });
}

export function deleteSharedDocument(documentId: string) {
  return apiRequest<void>(`/api/library/documents/${documentId}/`, {
    method: 'DELETE',
  });
}

export function downloadDocument(documentId: string, fallbackFilename = 'document') {
  return downloadFile(`/api/documents/${documentId}/download`, fallbackFilename);
}

export function downloadSharedDocument(documentId: string, fallbackFilename = 'document') {
  return downloadFile(`/api/library/documents/${documentId}/download/`, fallbackFilename);
}

export function useDocumentCategories() {
  return useQuery({
    queryKey: ['documentCategories'],
    queryFn: listDocumentCategories,
  });
}

export function useCreateDocumentCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createDocumentCategory,
    onSuccess: (category) => {
      queryClient.setQueryData<DocumentCategory[]>(['documentCategories'], (current = []) => (
        [...current.filter((item) => item.id !== category.id), category]
          .sort((left, right) => left.name.localeCompare(right.name))
      ));
    },
  });
}

export function useDocuments(projectId: number, query: string, categoryId: string, visibility: string) {
  return useQuery({
    queryKey: ['documents', projectId, query, categoryId, visibility],
    queryFn: () => listDocuments(projectId, query, categoryId, visibility),
    enabled: Boolean(projectId),
    placeholderData: (previous) => previous,
  });
}

export function useSharedDocuments(query: string, categoryId: string, enabled = true) {
  return useQuery({
    queryKey: ['shared-documents', query, categoryId],
    queryFn: () => listSharedDocuments(query, categoryId),
    enabled,
    placeholderData: (previous) => previous,
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

export function useSharedDocumentUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentUploadPayload) => uploadSharedDocument(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shared-documents'] }),
  });
}

export function useRenameDocument(projectId: number, standalone = false) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, payload }: { documentId: string; payload: DocumentRenamePayload }) =>
      standalone
        ? renameSharedDocument(documentId, payload)
        : renameDocument(projectId, documentId, payload),
    onSuccess: (document) => {
      queryClient.setQueryData(['document', projectId, document.id], document);
      queryClient.invalidateQueries({
        queryKey: standalone ? ['shared-documents'] : ['documents', projectId],
      });
    },
  });
}

export function useDeleteDocument(projectId: number, standalone = false) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => (
      standalone ? deleteSharedDocument(documentId) : deleteDocument(projectId, documentId)
    ),
    onSuccess: () => queryClient.invalidateQueries({
      queryKey: standalone ? ['shared-documents'] : ['documents', projectId],
    }),
  });
}
