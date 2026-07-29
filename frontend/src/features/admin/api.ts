import { apiRequest } from '../../shared/api/client';
import { downloadFile } from '../../shared/api/downloads';
import type { CurrentUser } from '../auth/AuthProvider';

export type PaginatedAccounts = {
  count: number;
  next: string | null;
  previous: string | null;
  results: CurrentUser[];
};

export function listAccounts(pageUrl?: string): Promise<PaginatedAccounts> {
  const path = pageUrl ?? '/api/accounts/admin/';
  return apiRequest<PaginatedAccounts>(path);
}

export function updateAccount(
  id: number,
  payload: { name?: string; global_role?: string },
): Promise<CurrentUser> {
  return apiRequest<CurrentUser>(`/api/accounts/admin/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function accountAction(
  id: number,
  action: 'suspend' | 'reactivate' | 'archive',
): Promise<CurrentUser> {
  return apiRequest<CurrentUser>(`/api/accounts/admin/${id}/`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

export type RoleActivation = {
  id: number;
  user: CurrentUser;
  requestedRole: 'teacher' | 'administrator';
  activationSource: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'revoked';
  createdAt: string;
  reviewedAt?: string | null;
  reviewer?: CurrentUser | null;
  reviewReason?: string;
};

export type PaginatedRoleActivations = {
  count: number;
  next: string | null;
  previous: string | null;
  results: RoleActivation[];
};

export function listRoleActivations({
  status = 'pending',
  query = '',
  pageUrl,
}: {
  status?: 'pending' | 'processed';
  query?: string;
  pageUrl?: string;
} = {}): Promise<PaginatedRoleActivations> {
  if (pageUrl) return apiRequest<PaginatedRoleActivations>(pageUrl);
  const params = new URLSearchParams({ status });
  if (query.trim()) params.set('q', query.trim());
  return apiRequest<PaginatedRoleActivations>(
    `/api/accounts/admin/role-activations/?${params.toString()}`,
  );
}

export function decideRoleActivation(
  id: number,
  action: 'approve' | 'reject' | 'revoke',
  reason = '',
) {
  return apiRequest<RoleActivation>(`/api/accounts/admin/role-activations/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ action, reason }),
  });
}

export type AuditEvent = {
  id: number;
  eventType: string;
  category: string;
  outcome: string;
  summary: string;
  reason?: string;
  correlationId?: string;
  actorSnapshot?: Record<string, unknown>;
  targetType?: string;
  targetId?: string;
  targetSnapshot?: Record<string, unknown>;
  createdAt?: string;
  capabilities?: { canExport: boolean };
};

export type AuditFilters = {
  q?: string;
  category?: string;
  outcome?: string;
  actorId?: string;
  projectId?: string;
  targetType?: string;
  targetId?: string;
};

export type AuditExport = {
  id: string;
  status: 'queued' | 'processing' | 'ready' | 'failed' | 'expired';
  requestedCount: number;
  exportedCount: number;
  failureReason?: string;
  expiresAt: string;
  capabilities: { canDownload: boolean; canRetry: boolean };
};

export function listAuditEvents(filters: AuditFilters = {}, cursor?: string | null) {
  const params = new URLSearchParams({ limit: '100' });
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) params.set(key, value.trim());
  }
  if (cursor) params.set('cursor', cursor);
  return apiRequest<{
    results: AuditEvent[];
    nextCursor: string | null;
    capabilities: { canExport: boolean };
  }>(`/api/audit-events?${params}`);
}

export function getAuditEvent(eventId: number) {
  return apiRequest<AuditEvent>(`/api/audit-events/${eventId}`);
}

export function createAuditExport(filters: AuditFilters) {
  return apiRequest<AuditExport>('/api/audit-exports', {
    method: 'POST',
    body: JSON.stringify({ filters }),
  });
}

export function getAuditExport(exportId: string) {
  return apiRequest<AuditExport>(`/api/audit-exports/${exportId}`);
}

export function downloadAuditExport(exportId: string) {
  return downloadFile(`/api/audit-exports/${exportId}/download`, 'audit-export.csv');
}

export type ProjectHealthRow = {
  projectId: number;
  title: string;
  advisorName: string;
  endsOn?: string | null;
  overdue: boolean;
  openTaskCount: number;
  overdueTaskCount: number;
  longBlockedTaskCount: number;
  missingReportCount: number;
  governanceState: 'normal' | 'hold';
  governanceHoldReason?: string;
  resourceConflictCount: number;
  notificationFailureCount: number;
  healthScore: number;
  healthLevel: 'healthy' | 'attention' | 'critical';
  actionPath: string;
};

export type ProjectHealthSnapshot = {
  generatedAt: string;
  windowDays: number;
  longBlockedDays: number;
  summary: {
    activeProjects: number;
    overdueProjects: number;
    overdueProjectRate: number;
    longBlockedTasks: number;
    missingReports: number;
    governanceHolds: number;
    resourceConflicts: number;
    notificationFailures: number;
    notificationFailureRate: number;
  };
  projects: ProjectHealthRow[];
  blockedTasks: Array<{
    taskId: number;
    title: string;
    projectId: number;
    projectTitle: string;
    blockedSince: string;
    blockedDays: number;
    deadlineAt?: string | null;
    actionPath: string;
  }>;
  missingReports: Array<{
    projectId: number;
    projectTitle: string;
    periodId: number;
    periodStart: string;
    deadlineAt: string;
    missingCount: number;
    actionPath: string;
  }>;
  governanceHolds: Array<{
    projectId: number;
    projectTitle: string;
    reason: string;
    startedAt?: string | null;
    actionPath: string;
  }>;
  trend: Array<{
    date: string;
    resourceConflicts: number;
    notificationFailures: number;
  }>;
};

export function getProjectHealthSnapshot() {
  return apiRequest<ProjectHealthSnapshot>('/api/admin/project-health/');
}
