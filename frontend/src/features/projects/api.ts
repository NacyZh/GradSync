import { apiRequest } from '../../shared/api/client';
import { downloadFile, type DownloadDescriptor } from '../../shared/api/downloads';

export type ProjectMaterial = {
  id: string;
  materialType: 'paper' | 'document' | 'code';
  backingRecordId: string;
  sourceProject: { id: string; title: string };
  visibility: 'project-only' | 'group-wide';
  classificationState: 'active' | 'pending_review' | 'archived';
  displayName?: string;
  actionCapabilities: {
    canView: boolean;
    canDownload: boolean;
    canRename?: boolean;
    canDelete?: boolean;
    canChangeVisibility: boolean;
  };
};

export type Project = {
  id: number;
  title: string;
  description: string;
  status: 'active' | 'archived';
  starts_on?: string | null;
  ends_on?: string | null;
  startsOn?: string | null;
  endsOn?: string | null;
  latestEventId?: string | null;
  freshness?: ProjectFreshness;
  generatedAt?: string;
  memberships?: ProjectMembership[];
  current_tasks?: unknown[];
  pending_reviews?: unknown[];
  upcoming_bookings?: unknown[];
  activity?: ProjectEvent[];
  capabilities?: ProjectCapabilities;
};

export type ProjectCapabilities = {
  canManageProject: boolean;
  canEditProject: boolean;
  canArchiveProject: boolean;
  canReopenProject: boolean;
  canDeleteProject: boolean;
  canManageMembers: boolean;
  canCreateTasks: boolean;
  canUpdateTasks: boolean;
  deleteDisabledReason?: string;
};

export type ProjectFreshness = {
  state: 'fresh' | 'stale' | 'refreshing';
  latestEventId?: string | null;
};

export type ProjectEvent = {
  id?: string;
  source?: string;
  event_type?: string;
  eventType?: string;
  targetType?: string;
  targetId?: string;
  summary: string;
  actor_id?: number | null;
  actorId?: number | null;
  created_at?: string;
  createdAt?: string;
};

export type ProjectListResponse = {
  results: Project[];
  capabilities?: {
    canCreateProject: boolean;
  };
};

export type ProjectMembership = {
  id: number;
  project_id?: number;
  user_id?: number;
  projectId?: number;
  userId?: number;
  nickname?: string;
  name?: string;
  email?: string;
  role: 'advisor' | 'student' | 'reviewer' | 'observer';
  status: 'active' | 'removed';
  joinedAt?: string;
  removedAt?: string | null;
};

export function listProjects() {
  return apiRequest<ProjectListResponse>('/api/projects/');
}

export function createProject(payload: { title: string; description?: string; starts_on?: string | null; ends_on?: string | null; student_ids?: number[]; studentIds?: number[] }) {
  return apiRequest<Project>('/api/projects/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: number) {
  return apiRequest<Project>(`/api/projects/${projectId}/`);
}

export function listProjectEvents(projectId: number, after?: string | null) {
  const suffix = after ? `?after=${encodeURIComponent(after)}` : '';
  return apiRequest<{ results: ProjectEvent[] }>(`/api/projects/${projectId}/events/${suffix}`);
}

export function updateProject(projectId: number, payload: Partial<Pick<Project, 'title' | 'description' | 'starts_on' | 'ends_on'>>) {
  return apiRequest<Project>(`/api/projects/${projectId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function archiveProject(projectId: number) {
  return apiRequest<Project>(`/api/projects/${projectId}/archive/`, { method: 'POST' });
}

export function reopenProject(projectId: number) {
  return apiRequest<Project>(`/api/projects/${projectId}/reopen/`, { method: 'POST' });
}

export function deleteProject(projectId: number) {
  return apiRequest<void>(`/api/projects/${projectId}/`, { method: 'DELETE' });
}

export function addProjectMember(projectId: number, payload: { studentId: number }) {
  return apiRequest<ProjectMembership>(`/api/projects/${projectId}/members/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function removeProjectMember(projectId: number, membershipId: number) {
  return apiRequest<void>(`/api/projects/${projectId}/members/${membershipId}/`, {
    method: 'DELETE',
  });
}

export type StudentOption = {
  id: number;
  nickname: string;
  email: string;
  degreeType: 'masters' | 'doctoral' | null;
  label: string;
  eligibility?: {
    selectable: boolean;
    reason: string;
  };
};

export function searchStudents(query: string, projectId?: number) {
  const params = new URLSearchParams({ q: query });
  if (projectId) params.set('projectId', String(projectId));
  return apiRequest<StudentOption[]>(`/api/accounts/students/?${params.toString()}`);
}

export function listProjectMaterials(projectId: number, filters: { type?: ProjectMaterial['materialType']; search?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set('type', filters.type);
  if (filters.search?.trim()) params.set('q', filters.search.trim());
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ count: number; results: ProjectMaterial[] }>(`/api/projects/${projectId}/materials/${suffix}`);
}

export function createProjectMaterial(projectId: number, payload: { materialType: ProjectMaterial['materialType']; file: File; title?: string; visibility: ProjectMaterial['visibility'] }) {
  const formData = new FormData();
  formData.append('materialType', payload.materialType);
  formData.append('file', payload.file);
  formData.append('visibility', payload.visibility);
  if (payload.title) formData.append('title', payload.title);
  return apiRequest<ProjectMaterial>(`/api/projects/${projectId}/materials/`, {
    method: 'POST',
    body: formData,
  });
}

export function updateProjectMaterialVisibility(projectId: number, materialId: string, payload: { visibility: ProjectMaterial['visibility']; reason?: string }) {
  return apiRequest<ProjectMaterial>(`/api/projects/${projectId}/materials/${materialId}/visibility/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function downloadProjectMaterial(projectId: number, materialId: string) {
  return downloadFile(`/api/projects/${projectId}/materials/${materialId}/download/`, 'project-material') as Promise<DownloadDescriptor>;
}
