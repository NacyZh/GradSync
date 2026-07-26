type Locale = 'en' | 'zh';
type Role = 'advisor' | 'co_advisor' | 'reviewer' | 'observer' | 'student' | 'administrator';

export function executionCapabilities(role: Role) {
  const manager = role === 'advisor' || role === 'co_advisor';
  return {
    canViewExecutionSummary: true,
    canManageMilestones: manager,
    canManageDeliverables: manager,
    canSubmitAssignedDeliverables: role === 'student',
    canRecommendDeliverables: manager || role === 'reviewer',
    canDecideDeliverables: manager,
    canManageReportTemplates: role === 'advisor',
    canViewReportAnalytics: true,
    canPublishDecisions: manager,
    canRaiseRisks: !['observer', 'administrator'].includes(role),
    canTriageRisks: manager,
    canManageProjectNotificationPolicy: role === 'advisor',
    canViewExecutionOperations: role === 'administrator',
  };
}

export function notificationPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    subject: 'Review required',
    category: 'project',
    requirementType: 'action',
    outcomeState: 'pending',
    status: 'in_app_only',
    eventType: 'pending_review',
    targetType: 'WeeklyProgressReport',
    targetId: '1',
    actionPath: '/projects/1/reports',
    eligibleAt: '2026-07-24T00:00:00Z',
    readAt: null,
    ...overrides,
  };
}

export function executionPayload(locale: Locale = 'en', role: Role = 'advisor') {
  return {
    projectId: 1,
    title: locale === 'zh' ? '研究执行' : 'Research execution',
    capabilities: executionCapabilities(role),
    milestones: [],
    deliverables: [],
  };
}

export function reportPayload(locale: Locale = 'en') {
  return {
    id: 1,
    title: locale === 'zh' ? '周期报告' : 'Periodic report',
    responses: [],
  };
}

export function riskPayload(locale: Locale = 'en') {
  return { id: 1, title: locale === 'zh' ? '样例风险' : 'Example risk', severity: 'medium' };
}

export function decisionPayload(locale: Locale = 'en') {
  return { id: 1, title: locale === 'zh' ? '样例决策' : 'Example decision', status: 'published' };
}
