import { apiRequest } from '../../shared/api/client';

export type NotificationRecord = {
  id: number;
  event_type: string;
  target_type: string;
  target_id: string;
  subject: string;
  action_path: string;
  status: string;
  eligible_at: string;
  sent_at?: string | null;
};

export function listProjectNotifications(projectId: number) {
  return apiRequest<{ results: NotificationRecord[] }>(`/api/projects/${projectId}/notifications/`);
}
