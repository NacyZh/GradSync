import { apiRequest } from '../../shared/api/client';

export type Task = {
  id: number;
  title: string;
  status: string;
  priority?: string;
  deadline_at?: string;
  assignee_id?: number;
  children?: Task[];
};

export function listProjectTasks(projectId: number) {
  return apiRequest<{ results: Task[] }>(`/api/projects/${projectId}/tasks/`);
}

export function createTask(projectId: number, payload: { title: string; assignee_id?: number; deadline_at?: string; priority?: string }) {
  return apiRequest<Task>(`/api/projects/${projectId}/tasks/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateTask(projectId: number, taskId: number, payload: Partial<Task>) {
  return apiRequest<Task>(`/api/projects/${projectId}/tasks/${taskId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
