import { apiRequest } from '../../shared/api/client';

export type NotificationRecord = {
  id: number;
  project_id?: number;
  projectId?: number;
  recipient_id?: number;
  recipientId?: number;
  event_type: string;
  eventType?: string;
  target_type: string;
  targetType?: string;
  target_id: string;
  targetId?: string;
  subject: string;
  action_path: string;
  actionPath?: string;
  status: string;
  eligible_at: string;
  eligibleAt?: string;
  sent_at?: string | null;
  sentAt?: string | null;
  failure_reason?: string | null;
  failureReason?: string | null;
  skipped_reason?: string | null;
  skippedReason?: string | null;
};

export function listProjectNotifications(projectId: number) {
  return apiRequest<{ results: NotificationRecord[] }>(`/api/projects/${projectId}/notifications/`);
}
