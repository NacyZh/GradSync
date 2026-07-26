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
  delivery_policy?: 'in_app' | 'in_app_email' | 'email_only';
  deliveryPolicy?: 'in_app' | 'in_app_email' | 'email_only';
  skipped_reason?: string | null;
  skippedReason?: string | null;
  readAt?: string | null;
  category?: NotificationCategory;
  requirementType?: NotificationRequirement;
  outcomeState?: NotificationOutcome;
  dueAt?: string | null;
  expiresAt?: string | null;
  acknowledgedAt?: string | null;
  actionCompletedAt?: string | null;
  activeFollowUp?: boolean;
  reminderCount?: number;
  escalationLevel?: number;
};

export type NotificationCategory = 'security' | 'project' | 'deliverable' | 'report' | 'decision' | 'risk' | 'schedule' | 'administration';
export type NotificationRequirement = 'informational' | 'acknowledgement' | 'action';
export type NotificationOutcome = 'not_required' | 'pending' | 'acknowledged' | 'completed' | 'expired' | 'unavailable';
export type NotificationFilters = {
  unread?: boolean;
  outcome?: NotificationOutcome;
  category?: NotificationCategory;
  projectId?: number;
  createdAfter?: string;
  cursor?: string;
  pageSize?: number;
};
export type NotificationPage = {
  results: NotificationRecord[];
  nextCursor?: string | null;
  unreadCount?: number;
  pendingActionCount?: number;
};
export type NotificationResponse = NotificationPage | NotificationRecord[];

export const notificationQueryKey = ['notifications'] as const;
export const notificationQueryKeys = {
  all: notificationQueryKey,
  list: (filters: NotificationFilters = {}) => ['notifications', 'list', filters] as const,
  preferences: ['notification-preferences'] as const,
  projectPolicy: (projectId: number) => ['project-notification-policy', projectId] as const,
};

export function listProjectNotifications(projectId: number) {
  return apiRequest<{ results: NotificationRecord[] }>(`/api/projects/${projectId}/notifications/`);
}

export function listNotifications(filters: NotificationFilters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value));
  }
  const suffix = params.size ? `?${params.toString()}` : '';
  return apiRequest<NotificationResponse>(`/api/notifications${suffix}`);
}

export function notificationResults(response?: NotificationResponse) {
  if (!response) return [];
  return Array.isArray(response) ? response : response.results;
}

export function markNotificationsRead(notificationIds: number[] | number) {
  const body = Array.isArray(notificationIds)
    ? { notificationIds }
    : { throughId: notificationIds };
  return apiRequest<{ throughId?: number | null; readAt: string; visibleCount: number; updatedIds: number[] }>(
    '/api/notifications/read',
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  );
}

export function acknowledgeNotification(notificationId: number) {
  return apiRequest<NotificationRecord>(
    `/api/notifications/${notificationId}/acknowledge`,
    { method: 'POST' },
  );
}

export type NotificationPreferences = {
  version: number;
  quietHoursEnabled: boolean;
  quietHoursStart?: string | null;
  quietHoursEnd?: string | null;
  timezone: string;
  categories: Array<{
    category: NotificationCategory;
    emailEnabled: boolean;
    emailRequired: boolean;
    inAppEnabled: true;
  }>;
};

export function getNotificationPreferences() {
  return apiRequest<NotificationPreferences>('/api/notification-preferences');
}

export function updateNotificationPreferences(payload: {
  expectedVersion: number;
  quietHoursEnabled: boolean;
  quietHoursStart?: string | null;
  quietHoursEnd?: string | null;
  timezone: string;
  categoryEmail: Partial<Record<NotificationCategory, boolean>>;
}) {
  return apiRequest<NotificationPreferences>('/api/notification-preferences', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export type ProjectNotificationPolicy = {
  version: number;
  reminderLeadMinutes: number;
  escalationDelayMinutes: number;
  repeatIntervalMinutes: number;
  maxReminders: number;
  usesSystemDefaults?: boolean;
  bounds?: { minimumMinutes: number; maximumMinutes: number };
  capabilities: { canEdit: boolean };
};

export function getProjectNotificationPolicy(projectId: number) {
  return apiRequest<ProjectNotificationPolicy>(
    `/api/projects/${projectId}/notification-policy`,
  );
}

export function updateProjectNotificationPolicy(
  projectId: number,
  payload: Omit<ProjectNotificationPolicy, 'usesSystemDefaults' | 'bounds' | 'capabilities' | 'version'> & { expectedVersion: number },
) {
  return apiRequest<ProjectNotificationPolicy>(
    `/api/projects/${projectId}/notification-policy`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
}
