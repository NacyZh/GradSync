import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadDescriptor } from '../../shared/api/downloads';

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
  status: string;
  latestVersion?: CodeArtifactVersion | null;
};

export type CodeArtifactPayload = {
  name: string;
  description?: string;
  tags?: string[];
  sourcePathLabel?: string;
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

export function listCodeArtifacts(projectId: number, query = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: CodeArtifact[] }>(`/api/projects/${projectId}/code-artifacts/${suffix}`);
}

export function createCodeArtifact(projectId: number, payload: CodeArtifactPayload) {
  return apiRequest<CodeArtifact>(`/api/projects/${projectId}/code-artifacts/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
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

export function useCodeArtifacts(projectId: number, query: string) {
  return useQuery({
    queryKey: ['codeArtifacts', projectId, query],
    queryFn: () => listCodeArtifacts(projectId, query),
    enabled: Boolean(projectId),
  });
}

export function useCreateCodeArtifact(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CodeArtifactPayload) => createCodeArtifact(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}

export function useImportCodeVersion(projectId: number, artifactId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CodeVersionPayload) => importCodeVersion(projectId, artifactId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['codeArtifacts', projectId] }),
  });
}
