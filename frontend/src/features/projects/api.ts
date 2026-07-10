import { apiRequest } from '../../shared/api/client';

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
  memberships?: ProjectMembership[];
  current_tasks?: unknown[];
  pending_reviews?: unknown[];
  upcoming_bookings?: unknown[];
  activity?: { event_type: string; summary: string; created_at: string }[];
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
  return apiRequest<{ results: Project[] }>('/api/projects/');
}

export function createProject(payload: { title: string; description?: string; starts_on?: string | null; ends_on?: string | null; student_ids?: number[] }) {
  return apiRequest<Project>('/api/projects/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: number) {
  return apiRequest<Project>(`/api/projects/${projectId}/`);
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
  degreeType: 'masters' | 'doctoral';
  label: string;
};

export function searchStudents(query: string) {
  return apiRequest<StudentOption[]>(`/api/accounts/students/?q=${encodeURIComponent(query)}`);
}

export function listProjectMaterials(projectId: number) {
  return apiRequest<{ count: number; results: ProjectMaterial[] }>(`/api/projects/${projectId}/materials/`);
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
