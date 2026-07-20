import { addDays, endOfDay, endOfMonth, endOfWeek, format, parseISO, startOfDay, startOfMonth, startOfWeek } from 'date-fns';

import { apiRequest } from '../../shared/api/client';

export type CalendarView = 'month' | 'week' | 'day' | 'agenda';
export type CalendarSource = 'schedule' | 'project' | 'task' | 'report' | 'booking';

export type ScheduleCapabilities = {
  canView: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canPublish: boolean;
  canCancel: boolean;
  canViewDeliveryStatus: boolean;
  isReadOnly: boolean;
};

export type CalendarOccurrence = {
  occurrenceId: string;
  sourceType: CalendarSource;
  sourceId: string;
  scheduleId?: number | null;
  scope: 'personal' | 'group' | 'system';
  category: string;
  title: string;
  description?: string;
  startsAt?: string | null;
  endsAt?: string | null;
  startsOn?: string | null;
  endsOn?: string | null;
  allDay: boolean;
  timezone: string;
  status: string;
  actionPath?: string | null;
  version?: number | null;
  capabilities: ScheduleCapabilities;
};

export type ScheduleRecurrence = {
  frequency: 'none' | 'daily' | 'weekly' | 'monthly';
  interval: number;
  weekdays: number[];
  until?: string | null;
};

export type ScheduleReminderInput = { offsetMinutes: number; mandatory?: boolean };
export type ScheduleAudienceSelection = { projectIds: number[]; accountIds: number[] };

export type ScheduleWrite = {
  scope: 'personal' | 'group';
  category: string;
  title: string;
  description: string;
  allDay: boolean;
  startsAt?: string | null;
  endsAt?: string | null;
  startsOn?: string | null;
  endsOn?: string | null;
  timezone: string;
  recurrence: ScheduleRecurrence;
  reminders: ScheduleReminderInput[];
  audience?: ScheduleAudienceSelection;
  confirmConflicts?: boolean;
};

export type ScheduleDetail = CalendarOccurrence & {
  id: number;
  owner: { id: number; name: string; role: string };
  organizer: { id: number; name: string; role: string };
  recurrence: ScheduleRecurrence;
  reminders: ScheduleReminderInput[];
  audience: ScheduleAudienceSelection;
  publishedAt?: string | null;
  cancelledAt?: string | null;
  version: number;
};

export type ScheduleChangeScope = 'occurrence' | 'future' | 'series';
export type ScheduleRevision = {
  id: number;
  revisionNumber: number;
  changeType: string;
  changedFields: string[];
  effectiveFrom: string;
  actor: { id: number; name: string; role: string };
  createdAt: string;
  audienceSummary: { projectCount: number; accountCount: number; resolvedRecipientCount: number };
};
export type ScheduleDeliveryStatus = {
  scheduleId: number;
  resolvedRecipients: { active: number; removed: number };
  notifications: {
    inAppCreated: number; inAppClaimed: number; emailSent: number;
    emailQueued: number; emailFailed: number; skipped: number;
  };
  deliveryPolicy: {
    publication: 'in_app'; ordinaryChange: 'in_app';
    cancellation: 'in_app_email'; reminder: 'in_app_email';
  };
  failureCodes: Array<{ code: string; count: number }>;
  updatedAt: string;
};
export type AudienceOption = {
  id: number;
  type: 'project' | 'account';
  label: string;
  secondaryLabel: string;
  role?: string | null;
  status: string;
  eligible: boolean;
  eligibilityScope: 'manageable_project_member' | 'active_account';
};

export type CalendarOccurrencePage = {
  results: CalendarOccurrence[];
  nextCursor: string | null;
  generatedAt: string;
  latestEventId: string;
};

export type CalendarEvent = {
  eventId: string;
  eventType: 'schedule_changed' | 'audience_changed' | 'source_changed' | 'notification_changed';
  scheduleId?: number | null;
  sourceType?: CalendarSource | null;
  sourceId?: string | null;
  occurredAt: string;
};

export type CalendarPeriod = { startsAt: string; endsAt: string };

export function calendarQueryKey(period: CalendarPeriod, sources: CalendarSource[]) {
  return ['calendar', period.startsAt, period.endsAt, ...sources.slice().sort()] as const;
}

export function periodForView(anchor: Date, view: CalendarView): CalendarPeriod {
  const startsAt = view === 'month'
    ? startOfWeek(startOfMonth(anchor), { weekStartsOn: 1 })
    : view === 'week'
      ? startOfWeek(anchor, { weekStartsOn: 1 })
      : startOfDay(anchor);
  const endsAt = view === 'month'
    ? endOfWeek(endOfMonth(anchor), { weekStartsOn: 1 })
    : view === 'week'
      ? endOfWeek(anchor, { weekStartsOn: 1 })
      : view === 'agenda'
        ? endOfDay(addDays(anchor, 61))
      : endOfDay(anchor);
  return { startsAt: startsAt.toISOString(), endsAt: endsAt.toISOString() };
}

export function occurrenceStart(occurrence: CalendarOccurrence): Date {
  return occurrence.startsAt ? parseISO(occurrence.startsAt) : parseISO(`${occurrence.startsOn}T00:00:00`);
}

export function formatOccurrenceTime(occurrence: CalendarOccurrence): string {
  if (occurrence.allDay) return 'All day';
  return occurrence.startsAt ? format(parseISO(occurrence.startsAt), 'HH:mm') : '';
}

export function listCalendarOccurrences(
  period: CalendarPeriod,
  sources: CalendarSource[],
  cursor?: string,
) {
  const params = new URLSearchParams({ startsAt: period.startsAt, endsAt: period.endsAt });
  if (sources.length) params.set('sources', sources.join(','));
  if (cursor) params.set('cursor', cursor);
  return apiRequest<CalendarOccurrencePage>(`/api/calendar/occurrences/?${params}`);
}

export function listCalendarEvents(since?: string) {
  const params = since ? `?since=${encodeURIComponent(since)}` : '';
  return apiRequest<{ results: CalendarEvent[]; latestEventId: string; generatedAt: string }>(`/api/calendar/events/${params}`);
}

export function calendarErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return 'Calendar is temporarily unavailable.';
}

export function createSchedule(payload: ScheduleWrite) {
  return apiRequest<ScheduleDetail>('/api/schedules/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function retrieveSchedule(scheduleId: number) {
  return apiRequest<ScheduleDetail>(`/api/schedules/${scheduleId}/`);
}

export function updateSchedule(
  scheduleId: number,
  payload: { expectedVersion: number; changeScope: ScheduleChangeScope; occurrenceKey?: string | null; fields: Partial<ScheduleWrite>; confirmConflicts?: boolean },
) {
  return apiRequest<ScheduleDetail>(`/api/schedules/${scheduleId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function completeSchedule(scheduleId: number, expectedVersion: number, changeScope: ScheduleChangeScope, occurrenceKey?: string | null) {
  return apiRequest<ScheduleDetail>(`/api/schedules/${scheduleId}/complete/`, {
    method: 'POST',
    body: JSON.stringify({ expectedVersion, changeScope, occurrenceKey, confirmed: true }),
  });
}

export function deleteSchedule(scheduleId: number, expectedVersion: number, changeScope: ScheduleChangeScope, occurrenceKey?: string | null) {
  return apiRequest<void>(`/api/schedules/${scheduleId}/`, {
    method: 'DELETE',
    body: JSON.stringify({ expectedVersion, changeScope, occurrenceKey, confirmed: true }),
  });
}

export function cancelSchedule(scheduleId: number, expectedVersion: number, changeScope: ScheduleChangeScope, occurrenceKey?: string | null, reason = '') {
  return apiRequest<ScheduleDetail>(`/api/schedules/${scheduleId}/cancel/`, {
    method: 'POST',
    body: JSON.stringify({ expectedVersion, changeScope, occurrenceKey, reason, confirmed: true }),
  });
}

export function listScheduleRevisions(scheduleId: number) {
  return apiRequest<{ count: number; results: ScheduleRevision[] }>(`/api/schedules/${scheduleId}/revisions/`);
}

export function retrieveScheduleDeliveryStatus(scheduleId: number) {
  return apiRequest<ScheduleDeliveryStatus>(`/api/schedules/${scheduleId}/delivery-status/`);
}

export function checkScheduleConflicts(payload: Pick<ScheduleWrite, 'allDay' | 'startsAt' | 'endsAt' | 'startsOn' | 'endsOn' | 'timezone'> & { scheduleId?: number }) {
  return apiRequest<{ results: Array<{ occurrenceId: string; title: string }> }>('/api/schedules/conflicts/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listAudienceOptions(type: 'project' | 'account', query: string) {
  const params = new URLSearchParams({ type, q: query, limit: '20' });
  return apiRequest<{ results: AudienceOption[]; nextCursor: string | null }>(`/api/schedules/audience-options/?${params}`);
}

export function publishSchedule(scheduleId: number, expectedVersion: number, audience: ScheduleAudienceSelection, reminders: ScheduleReminderInput[]) {
  return apiRequest<ScheduleDetail>(`/api/schedules/${scheduleId}/publish/`, {
    method: 'POST',
    body: JSON.stringify({ expectedVersion, audience, reminders, confirmed: true }),
  });
}
