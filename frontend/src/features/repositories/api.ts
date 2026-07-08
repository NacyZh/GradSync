import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadDescriptor, type DownloadDescriptor } from '../../shared/api/downloads';

export type CodeArtifactVersion = {
  id: string;
  artifactId: string;
  projectId: string;
  versionLabel?: string;
  commitReference?: string;
  releaseNotes?: string;
  description?: string;
  filename: string;
  relativePathManifest?: string[];
  checksumSha256: string;
  status: string;
};

export type CodeArtifact = {
  id: string;
  projectId: string;
  name: string;
  description?: string;
  tags?: string[];
  sourcePathLabel?: string;
  visibility: 'project_members' | 'group_wide';
  checksumSha256?: string;
  archiveFileId?: string;
  status: string;
  latestVersion?: CodeArtifactVersion | null;
  actionCapabilities?: {
    canView: boolean;
    canDownload: boolean;
    canRename: boolean;
    canDelete: boolean;
  };
};

export type CodeArtifactPayload = {
  name: string;
  description?: string;
  tags?: string[];
  sourcePathLabel?: string;
  visibility?: 'project_members' | 'group_wide';
};

export type CodeArtifactUploadPayload = {
  archive: File;
  name: string;
  description: string;
  tags?: string;
  visibility: 'project_members' | 'group_wide';
};

export type CodeArtifactUploadPolicy = {
  category: string;
  maxSizeBytes: number;
  displayLabel: string;
  allowedExtensions: string[];
  contentTypes: string[];
};

export type CodeArtifactRenamePayload = {
  name: string;
  reason?: string;
};

export type CodeVersionPayload = {
  versionLabel?: string;
  commitReference?: string;
  releaseNotes?: string;
  description?: string;
  sourceType?: 'local_folder' | 'local_archive';
  sourcePathLabel?: string;
  relativePathManifest?: string[];
  filename: string;
  contentType?: string;
  sizeBytes?: number;
  checksumSha256: string;
};

export function listCodeArtifacts(projectId: number, query = '', visibility = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (visibility) params.set('visibility', visibility);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: CodeArtifact[] }>(`/api/projects/${projectId}/code-artifacts/${suffix}`);
}

export function createCodeArtifact(projectId: number, payload: CodeArtifactPayload) {
  return apiRequest<CodeArtifact>(`/api/projects/${projectId}/code-artifacts/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function retrieveCodeArtifact(projectId: number, artifactId: string) {
  return apiRequest<CodeArtifact>(`/api/projects/${projectId}/code-artifacts/${artifactId}/`);
}

export function renameCodeArtifact(projectId: number, artifactId: string, payload: CodeArtifactRenamePayload) {
  return apiRequest<CodeArtifact>(`/api/projects/${projectId}/code-artifacts/${artifactId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteCodeArtifact(projectId: number, artifactId: string) {
  return apiRequest<void>(`/api/projects/${projectId}/code-artifacts/${artifactId}/`, {
    method: 'DELETE',
  });
}

export function uploadCodeArtifact(projectId: number, payload: CodeArtifactUploadPayload) {
  const formData = new FormData();
  formData.append('archive', payload.archive);
  formData.append('name', payload.name);
  formData.append('description', payload.description);
  formData.append('visibility', payload.visibility);
  if (payload.tags) formData.append('tags', payload.tags);
  return apiRequest<CodeArtifact>(`/api/projects/${projectId}/code-artifacts/`, {
    method: 'POST',
    body: formData,
  });
}

export function getCodeArtifactUploadPolicy() {
  return apiRequest<CodeArtifactUploadPolicy>('/api/code-artifacts/upload-policy/');
}

export function importCodeVersion(projectId: number, artifactId: string, payload: CodeVersionPayload) {
  return apiRequest<CodeArtifactVersion>(`/api/projects/${projectId}/code-artifacts/${artifactId}/versions/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function downloadCodeVersion(projectId: number, artifactId: string, versionId: string) {
  return downloadDescriptor(`/api/projects/${projectId}/code-artifacts/${artifactId}/versions/${versionId}/download/`);
}

export function downloadCodeArtifact(projectId: number, artifact: CodeArtifact): Promise<DownloadDescriptor> {
  if (artifact.archiveFileId) {
    return apiRequest<DownloadDescriptor>(`/api/code-artifacts/${artifact.id}/download`);
  }
  if (artifact.latestVersion) {
    return downloadCodeVersion(projectId, artifact.id, artifact.latestVersion.id);
  }
  return Promise.reject(new Error('No archive is available for this code artifact'));
}

export function useCodeArtifacts(projectId: number, query: string, visibility = '') {
  return useQuery({
    queryKey: ['codeArtifacts', projectId, query, visibility],
    queryFn: () => listCodeArtifacts(projectId, query, visibility),
    enabled: Boolean(projectId),
  });
}

export function useCodeArtifact(projectId: number, artifactId?: string) {
  return useQuery({
    queryKey: ['codeArtifact', projectId, artifactId],
    queryFn: () => retrieveCodeArtifact(projectId, artifactId as string),
    enabled: Boolean(projectId && artifactId),
  });
}

export function useCreateCodeArtifact(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CodeArtifactPayload) => createCodeArtifact(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}

export function useRenameCodeArtifact(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ artifactId, payload }: { artifactId: string; payload: CodeArtifactRenamePayload }) =>
      renameCodeArtifact(projectId, artifactId, payload),
    onSuccess: (artifact) => {
      queryClient.setQueryData(['codeArtifact', projectId, artifact.id], artifact);
      queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] });
    },
  });
}

export function useDeleteCodeArtifact(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (artifactId: string) => deleteCodeArtifact(projectId, artifactId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}

export function useCodeArtifactUpload(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CodeArtifactUploadPayload) => uploadCodeArtifact(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}

export function useCodeArtifactUploadPolicy() {
  return useQuery({
    queryKey: ['code-artifact-upload-policy'],
    queryFn: getCodeArtifactUploadPolicy,
  });
}

export function useImportCodeVersion(projectId: number, artifactId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CodeVersionPayload) => importCodeVersion(projectId, artifactId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}
