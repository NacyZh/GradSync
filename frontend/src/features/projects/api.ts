import { apiRequest } from '../../shared/api/client';

export type Project = {
  id: number;
  title: string;
  description: string;
  status: 'active' | 'archived';
  memberships?: ProjectMembership[];
  current_tasks?: unknown[];
  pending_reviews?: unknown[];
  upcoming_bookings?: unknown[];
  activity?: { event_type: string; summary: string; created_at: string }[];
};

export type ProjectMembership = {
  id: number;
  project_id: number;
  user_id: number;
  role: 'advisor' | 'student' | 'reviewer' | 'observer';
  status: 'active' | 'removed';
};

export function listProjects() {
  return apiRequest<{ results: Project[] }>('/api/projects/');
}

export function createProject(payload: { title: string; description?: string; student_ids?: number[] }) {
  return apiRequest<Project>('/api/projects/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: number) {
  return apiRequest<Project>(`/api/projects/${projectId}/`);
}

export function updateProject(projectId: number, payload: Partial<Pick<Project, 'title' | 'description'>>) {
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

export function addProjectMember(projectId: number, payload: { user_id: number; role: ProjectMembership['role'] }) {
  return apiRequest<ProjectMembership>(`/api/projects/${projectId}/members/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
