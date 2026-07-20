import { apiRequest } from '../../shared/api/client';

export type NotificationStatus = 'pending' | 'queued' | 'sent' | 'failed' | 'retry_needed' | 'skipped' | 'in_app_only';

export type NotificationRecord = {
  id: number;
  project_id?: number;
  projectId?: number;
  recipient_id?: number;
  recipientId?: number;
  recipient_email?: string;
  recipientEmail?: string;
  event_type: string;
  eventType?: string;
  target_type: string;
  targetType?: string;
  relatedObjectType?: string;
  target_id: string;
  targetId?: string;
  relatedObjectId?: string;
  subject: string;
  action_path: string;
  actionPath?: string;
  status: NotificationStatus;
  eligible_at: string;
  eligibleAt?: string;
  queued_at?: string | null;
  queuedAt?: string | null;
  sent_at?: string | null;
  sentAt?: string | null;
  last_attempt_at?: string | null;
  lastAttemptAt?: string | null;
  retry_count?: number;
  retryCount?: number;
  failure_reason?: string | null;
  failureReason?: string | null;
  delivery_policy?: 'in_app' | 'in_app_email';
  deliveryPolicy?: 'in_app' | 'in_app_email';
  skipped_reason?: string | null;
  skippedReason?: string | null;
};

export function listProjectNotifications(projectId: number) {
  return apiRequest<{ results: NotificationRecord[] }>(`/api/projects/${projectId}/notifications/`);
}

export function listNotifications() {
  return apiRequest<{ results: NotificationRecord[] } | NotificationRecord[]>('/api/notifications');
}
