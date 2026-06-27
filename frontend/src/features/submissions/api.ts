import { apiRequest } from '../../shared/api/client';

export type DraftVersion = {
  id: number;
  version_number: number;
  review_status: string;
  content_reference?: string;
};

export type Draft = {
  id: number;
  title: string;
  status: string;
};

export type WeeklyReport = {
  id: number;
  report_week_start: string;
  completed_work: string;
  next_steps: string;
  review_status: string;
};

export type InlineComment = {
  id: number;
  target_type: string;
  target_id: number;
  anchor: string;
  body: string;
  status: string;
};

export function listDrafts(projectId: number) {
  return apiRequest<{ results: Draft[] }>(`/api/projects/${projectId}/drafts/`);
}

export function createDraft(projectId: number, title: string) {
  return apiRequest<Draft>(`/api/projects/${projectId}/drafts/`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export function submitDraftVersion(projectId: number, draftId: number, payload: { content_reference: string; summary?: string }) {
  return apiRequest<DraftVersion>(`/api/projects/${projectId}/drafts/${draftId}/versions/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function reviewDraftVersion(projectId: number, draftId: number, versionId: number, review_status: string) {
  return apiRequest<DraftVersion>(`/api/projects/${projectId}/drafts/${draftId}/versions/${versionId}/review/`, {
    method: 'PATCH',
    body: JSON.stringify({ review_status }),
  });
}

export function listReports(projectId: number) {
  return apiRequest<{ results: WeeklyReport[] }>(`/api/projects/${projectId}/reports/`);
}

export function submitWeeklyReport(projectId: number, payload: { report_week_start: string; completed_work: string; blockers?: string; next_steps: string }) {
  return apiRequest<WeeklyReport>(`/api/projects/${projectId}/reports/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function reviewWeeklyReport(projectId: number, reportId: number, review_status: string) {
  return apiRequest<WeeklyReport>(`/api/projects/${projectId}/reports/${reportId}/review/`, {
    method: 'PATCH',
    body: JSON.stringify({ review_status }),
  });
}

export function listComments(projectId: number, target_type?: string, target_id?: number) {
  const params = new URLSearchParams();
  if (target_type) params.set('target_type', target_type);
  if (target_id) params.set('target_id', String(target_id));
  const query = params.toString();
  return apiRequest<{ results: InlineComment[] }>(`/api/projects/${projectId}/comments/${query ? `?${query}` : ''}`);
}

export function createComment(projectId: number, payload: { target_type: string; target_id: number; anchor: string; body: string }) {
  return apiRequest<InlineComment>(`/api/projects/${projectId}/comments/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateCommentStatus(projectId: number, commentId: number, status: string) {
  return apiRequest<InlineComment>(`/api/projects/${projectId}/comments/${commentId}/status/`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
