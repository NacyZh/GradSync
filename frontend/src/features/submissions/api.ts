import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../../shared/api/client';
import { downloadFile } from '../../shared/api/downloads';

export type WeeklyReport = {
  id: number;
  report_week_start: string;
  completed_work: string;
  blockers?: string;
  next_steps: string;
  revision_number?: number;
  review_status: string;
  submitted_at?: string;
  reviewed_at?: string | null;
};

export type ReportTemplateField = {
  id: number;
  key: string;
  labelEn: string;
  labelZh: string;
  helpTextEn?: string;
  helpTextZh?: string;
  fieldType: 'long_text' | 'number' | 'percentage' | 'single_choice' | 'multiple_choice' | 'execution_progress' | 'risk_blocker';
  required: boolean;
  order: number;
  unit?: string;
  options: Array<{ value: string; labelEn: string; labelZh: string }>;
  minValue?: string | null;
  maxValue?: string | null;
  analyticsEnabled: boolean;
};

export type ReportTemplateVersion = {
  id: number;
  templateId: number;
  projectId: number;
  name: string;
  versionNumber: number;
  status: 'draft' | 'published' | 'superseded';
  version: number;
  fields: ReportTemplateField[];
  publishedAt?: string | null;
};

export type ReportingPeriod = {
  id: number;
  projectId: number;
  startsOn: string;
  endsOn: string;
  deadlineAt: string;
  templateVersionId: number;
  state: 'open' | 'closed';
  currentUserReportStatus?: 'missing' | WeeklyReport['review_status'] | null;
};

export type StructuredReport = {
  id: number;
  projectId: number;
  student: { id: number; displayName: string; role: string };
  reportingPeriod: ReportingPeriod;
  templateVersionId: number;
  revisionNumber: number;
  reviewStatus: string;
  submittedAt: string;
  submittedLate: boolean;
  responses: Array<{ fieldId: number; value: unknown; sourceType?: string; sourceId?: string }>;
};

export type ReportAnalytics = {
  projectId: number;
  from: string;
  to: string;
  submissionCounts: Record<string, number>;
  reviewCounts?: Record<string, number>;
  metricSeries: Array<{
    key: string;
    labelEn: string;
    labelZh: string;
    value: number | null;
    unit: string;
    population: number;
    missing: number;
    sourceReportIds: number[];
  }>;
};

export function listReportTemplates(projectId: number) {
  return apiRequest<{
    results: ReportTemplateVersion[];
    capabilities: {
      canEditTemplate: boolean;
      canPublishTemplate: boolean;
      canSubmitReport: boolean;
      canViewAnalytics: boolean;
      canExportAnalytics: boolean;
    };
  }>(`/api/projects/${projectId}/report-templates/`);
}

export function createReportTemplateDraft(projectId: number, name: string) {
  return apiRequest<ReportTemplateVersion>(`/api/projects/${projectId}/report-templates/`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function updateReportTemplate(
  projectId: number,
  template: ReportTemplateVersion,
  fields: ReportTemplateField[],
) {
  return apiRequest<ReportTemplateVersion>(
    `/api/projects/${projectId}/report-templates/${template.id}/`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        expectedVersion: template.version,
        name: template.name,
        fields,
      }),
    },
  );
}

export function publishReportTemplate(projectId: number, template: ReportTemplateVersion) {
  return apiRequest<ReportTemplateVersion>(
    `/api/projects/${projectId}/report-templates/${template.id}/publish/`,
    {
      method: 'POST',
      body: JSON.stringify({ expectedVersion: template.version, reason: 'Published for future periods' }),
    },
  );
}

export function listReportingPeriods(projectId: number) {
  return apiRequest<{ results: ReportingPeriod[]; page: { nextCursor: string | null } }>(
    `/api/projects/${projectId}/reporting-periods/?pageSize=100`,
  );
}

export function submitStructuredReport(
  projectId: number,
  payload: {
    reportingPeriodId: number;
    responses: Array<{ fieldId: number; value: unknown }>;
    idempotencyKey: string;
  },
) {
  return apiRequest<StructuredReport>(`/api/projects/${projectId}/reports/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getReportAnalytics(projectId: number, from: string, to: string) {
  return apiRequest<ReportAnalytics>(
    `/api/projects/${projectId}/report-analytics/?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
  );
}

export function downloadReportAnalytics(projectId: number, from: string, to: string) {
  return downloadFile(
    `/api/projects/${projectId}/report-analytics/export/?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
    `project-${projectId}-report-analytics.csv`,
  );
}

export type ProjectReportSchedule = {
  id: number;
  projectId: number;
  weekday: number;
  deadlineLocalTime: string;
  timezone: string;
  version: number;
  updatedBy: { id: number; name: string; role: string };
  createdAt: string;
  updatedAt: string;
};

export type InlineComment = {
  id: number;
  target_type: string;
  target_id: number;
  anchor: string;
  body: string;
  status: string;
};

export type ReviewAssignment = {
  id: string;
  reviewerMembershipId: number;
  reviewerName?: string;
  weeklyReportId?: number | null;
  writingVersionId?: number | null;
  draftVersionId?: number | null;
  deliverableRevisionId?: number | null;
  status: 'active' | 'removed';
  version: number;
};

export function listReviewAssignments(projectId: number) {
  return apiRequest<{ results: ReviewAssignment[] }>(
    `/api/projects/${projectId}/review-assignments/`,
  );
}

export function assignReportReviewer(
  projectId: number,
  payload: { reviewerMembershipId: number; weeklyReportId: number },
) {
  return apiRequest<ReviewAssignment>(
    `/api/projects/${projectId}/review-assignments/`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

export function removeReviewAssignment(
  projectId: number,
  assignmentId: string,
  expectedVersion: number,
) {
  return apiRequest<void>(
    `/api/projects/${projectId}/review-assignments/${assignmentId}/?expectedVersion=${expectedVersion}`,
    { method: 'DELETE' },
  );
}

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
  legacyProjectId?: string | null;
  studentId: string;
  title: string;
  writingType: 'thesis' | 'manuscript' | 'paper' | 'other';
  participantRole?: 'student_author' | 'bound_advisor' | 'assigned_reviewer' | 'administrator' | '';
  status: 'active' | 'closed' | 'archived';
  versions: WritingVersion[];
};

export function listReports(projectId: number) {
  return apiRequest<{ results: WeeklyReport[] }>(`/api/projects/${projectId}/reports/`);
}

export function submitWeeklyReport(projectId: number, payload: { report_week_start: string; completed_work: string; blockers?: string; next_steps: string }) {
  return apiRequest<WeeklyReport>(`/api/projects/${projectId}/reports/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProjectReportSchedule(projectId: number) {
  return apiRequest<ProjectReportSchedule | undefined>(`/api/projects/${projectId}/report-schedule/`);
}

export function saveProjectReportSchedule(
  projectId: number,
  payload: { weekday: number; deadlineLocalTime: string; timezone: string; expectedVersion?: number },
) {
  return apiRequest<ProjectReportSchedule>(`/api/projects/${projectId}/report-schedule/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteProjectReportSchedule(projectId: number, expectedVersion: number) {
  return apiRequest<void>(`/api/projects/${projectId}/report-schedule/`, {
    method: 'DELETE',
    body: JSON.stringify({ expectedVersion }),
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

function writingProjectsPath(projectId?: number) {
  return projectId ? `/api/projects/${projectId}/writing-projects/` : '/api/writing-projects/';
}

export function listWritingProjects(projectId?: number, query = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{ results: WritingProject[] }>(`${writingProjectsPath(projectId)}${suffix}`);
}

export function createWritingProject(projectId: number | undefined, payload: { title: string; writingType: WritingProject['writingType'] }) {
  return apiRequest<WritingProject>(writingProjectsPath(projectId), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function renameWritingProject(projectId: number | undefined, writingProjectId: string, payload: { title: string }) {
  return apiRequest<WritingProject>(`${writingProjectsPath(projectId)}${writingProjectId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteWritingProject(projectId: number | undefined, writingProjectId: string) {
  return apiRequest<void>(`${writingProjectsPath(projectId)}${writingProjectId}/`, {
    method: 'DELETE',
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

export function downloadWritingVersion(versionId: string, fallbackFilename = 'writing-version') {
  return downloadFile(`/api/writing-versions/${versionId}/download`, fallbackFilename);
}

export function downloadTeacherFeedback(feedbackId: string, fallbackFilename = 'teacher-feedback') {
  return downloadFile(`/api/teacher-feedback/${feedbackId}/download`, fallbackFilename);
}

export function useWritingProjects(projectId?: number, query = '') {
  return useQuery({
    queryKey: ['writingProjects', projectId ?? 'standalone', query],
    queryFn: () => listWritingProjects(projectId, query),
  });
}

export function useCreateWritingProject(projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; writingType: WritingProject['writingType'] }) => createWritingProject(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId ?? 'standalone'] }),
  });
}

export function useRenameWritingProject(projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ writingProjectId, title }: { writingProjectId: string; title: string }) => renameWritingProject(projectId, writingProjectId, { title }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId ?? 'standalone'] }),
  });
}

export function useDeleteWritingProject(projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (writingProjectId: string) => deleteWritingProject(projectId, writingProjectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId ?? 'standalone'] }),
  });
}

export function useUploadWritingVersion(projectId: number | undefined, writingProjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { file: File; summary?: string }) => uploadWritingVersion(writingProjectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId ?? 'standalone'] }),
  });
}

export function useSubmitTeacherFeedback(projectId: number | undefined, writingVersionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { annotatedFile: File; comments?: string }) => submitTeacherFeedback(writingVersionId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['writingProjects', projectId ?? 'standalone'] }),
  });
}
