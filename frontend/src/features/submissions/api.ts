import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import type { DownloadDescriptor } from '../../shared/api/downloads';

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

export type TeacherFeedback = {
  id: string;
  writingVersionId: string;
  reviewerId: string;
  comments?: string;
  status: 'draft' | 'submitted' | 'notification_pending' | 'notification_sent' | 'notification_failed';
  annotatedFileId?: string;
  annotatedFileName?: string;
  notificationStatus?: string;
};

export type WritingVersion = {
  id: string;
  writingProjectId: string;
  versionNumber: number;
  submittedById?: string;
  draftFileId?: string;
  draftFileName?: string;
  fileKind?: 'word' | 'latex_source' | 'latex_archive';
  summary?: string;
  status: 'submitted' | 'under_review' | 'feedback_available' | 'closed';
  submittedAt?: string;
  feedback?: TeacherFeedback[];
};

export type WritingProject = {
  id: string;
  projectId: string;
  studentId: string;
  title: string;
  writingType: 'thesis' | 'manuscript' | 'paper' | 'other';
  status: 'active' | 'closed' | 'archived';
  versions: WritingVersion[];
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

export function listWritingProjects(projectId: number, query = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: WritingProject[] }>(`/api/projects/${projectId}/writing-projects/${suffix}`);
}

export function createWritingProject(projectId: number, payload: { title: string; writingType: WritingProject['writingType'] }) {
  return apiRequest<WritingProject>(`/api/projects/${projectId}/writing-projects/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function uploadWritingVersion(writingProjectId: string, payload: { file: File; summary?: string }) {
  const formData = new FormData();
  formData.append('file', payload.file);
  if (payload.summary) formData.append('summary', payload.summary);
  return apiRequest<WritingVersion>(`/api/writing-projects/${writingProjectId}/versions`, {
    method: 'POST',
    body: formData,
  });
}

export function submitTeacherFeedback(writingVersionId: string, payload: { annotatedFile: File; comments?: string }) {
  const formData = new FormData();
  formData.append('annotatedFile', payload.annotatedFile);
  if (payload.comments) formData.append('comments', payload.comments);
  return apiRequest<TeacherFeedback>(`/api/writing-versions/${writingVersionId}/feedback`, {
    method: 'POST',
    body: formData,
  });
}

export function downloadTeacherFeedback(feedbackId: string) {
  return apiRequest<DownloadDescriptor>(`/api/teacher-feedback/${feedbackId}/download`);
}

export function useWritingProjects(projectId: number, query = '') {
  return useQuery({
    queryKey: ['writingProjects', projectId, query],
    queryFn: () => listWritingProjects(projectId, query),
    enabled: Boolean(projectId),
  });
}

export function useCreateWritingProject(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; writingType: WritingProject['writingType'] }) => createWritingProject(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId] }),
  });
}

export function useUploadWritingVersion(projectId: number, writingProjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { file: File; summary?: string }) => uploadWritingVersion(writingProjectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId] }),
  });
}

export function useSubmitTeacherFeedback(projectId: number, writingVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { annotatedFile: File; comments?: string }) => submitTeacherFeedback(writingVersionId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId] }),
  });
}
