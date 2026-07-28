import { apiRequest } from '../../shared/api/client';

export type ExecutionCapabilities = {
  canManageMilestones: boolean;
  canManageDeliverables: boolean;
  canSubmitAssignedDeliverables: boolean;
  canRecommendDeliverables: boolean;
  canDecideDeliverables: boolean;
  canPublishDecisions: boolean;
  canRaiseRisks: boolean;
  canTriageRisks: boolean;
};

export type ExecutionSummary = {
  projectId: number;
  milestoneCounts: Record<string, number>;
  deliverableCounts: Record<string, number>;
  riskCounts: Record<string, number>;
  pendingReviews: number;
  missingReports: number;
  unresolvedActions: number;
  upcoming: Array<{
    type: 'milestone' | 'deliverable' | 'risk' | 'report';
    id: number;
    title: string;
    dueDate: string;
  }>;
  capabilities: ExecutionCapabilities;
};

export type Milestone = {
  id: number;
  projectId: number;
  title: string;
  description: string;
  targetDate: string;
  ownerIds: number[];
  order: number;
  status:
    | 'planned'
    | 'in_progress'
    | 'at_risk'
    | 'blocked'
    | 'overdue'
    | 'completed'
    | 'archived';
  version: number;
  requiredDeliverables: number;
  acceptedDeliverables: number;
  completedAt: string | null;
  archivedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ExecutionMember = {
  id: number;
  name: string;
  role?: string;
};

export type DeliverableEvidence = {
  id: number;
  type: 'project_material' | 'task' | 'weekly_progress_report' | 'external_url';
  sourceId: number | null;
  url?: string;
  label: string;
  available: boolean;
  sourceTypeSnapshot: string;
  sourceIdSnapshot: string;
};

export type DeliverableRevision = {
  id: number;
  revisionNumber: number;
  state:
    | 'submitted'
    | 'recommended_accept'
    | 'recommended_return'
    | 'accepted'
    | 'returned';
  criteriaSnapshot: string;
  descriptionSnapshot: string;
  submittedBy: ExecutionMember;
  submittedAt: string;
  evidence: DeliverableEvidence[];
  recommendations: Array<{
    id: number;
    revisionId: number;
    recommendation: 'accept' | 'return';
    rationale: string;
    reviewer: ExecutionMember;
    createdAt: string;
  }>;
  finalDecision?: {
    id: number;
    revisionId: number;
    decision: 'accepted' | 'returned';
    rationale: string;
    decidedBy: ExecutionMember;
    decidedAt: string;
  } | null;
};

export type Deliverable = {
  id: number;
  projectId: number;
  milestoneId: number;
  title: string;
  description: string;
  acceptanceCriteria: string;
  dueDate: string;
  required: boolean;
  reviewerRequired: boolean;
  status:
    | 'planned'
    | 'in_progress'
    | 'blocked'
    | 'submitted'
    | 'under_review'
    | 'changes_requested'
    | 'accepted'
    | 'archived';
  progressPercent: number;
  blockerSummary: string;
  assignees: ExecutionMember[];
  taskIds: number[];
  version: number;
  acceptedRevisionId: number | null;
  revisions: DeliverableRevision[];
  capabilities: ExecutionCapabilities;
};

type CursorPage<T> = {
  results: T[];
  page: { nextCursor: string | null };
  capabilities: ExecutionCapabilities;
};

function queryString(filters: Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function getExecutionSummary(projectId: number) {
  return apiRequest<ExecutionSummary>(
    `/api/projects/${projectId}/execution-summary/`,
  );
}

export function listMilestones(
  projectId: number,
  filters: {
    q?: string;
    status?: string;
    includeArchived?: boolean;
    cursor?: string;
    pageSize?: number;
  } = {},
) {
  return apiRequest<CursorPage<Milestone>>(
    `/api/projects/${projectId}/milestones/${queryString(filters)}`,
  );
}

export function createMilestone(
  projectId: number,
  payload: {
    title: string;
    description?: string;
    targetDate: string;
    ownerIds: number[];
  },
) {
  return apiRequest<Milestone>(`/api/projects/${projectId}/milestones/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateMilestone(
  projectId: number,
  milestoneId: number,
  payload: Partial<{
    title: string;
    description: string;
    targetDate: string;
    ownerIds: number[];
  }> & { expectedVersion: number },
) {
  return apiRequest<Milestone>(
    `/api/projects/${projectId}/milestones/${milestoneId}/`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
}

export function archiveMilestone(
  projectId: number,
  milestoneId: number,
  expectedVersion: number,
) {
  return apiRequest<Milestone>(
    `/api/projects/${projectId}/milestones/${milestoneId}/archive/`,
    {
      method: 'POST',
      body: JSON.stringify({ expectedVersion }),
    },
  );
}

export function listDeliverables(
  projectId: number,
  filters: {
    milestoneId?: number;
    status?: string;
    q?: string;
    includeArchived?: boolean;
    cursor?: string;
    pageSize?: number;
  } = {},
) {
  return apiRequest<CursorPage<Deliverable>>(
    `/api/projects/${projectId}/deliverables/${queryString(filters)}`,
  );
}

export function createDeliverable(
  projectId: number,
  payload: {
    milestoneId: number;
    title: string;
    description?: string;
    acceptanceCriteria: string;
    dueDate: string;
    required: boolean;
    assigneeIds: number[];
    reviewerRequired?: boolean;
    reviewerIds?: number[];
    taskIds?: number[];
  },
) {
  return apiRequest<Deliverable>(`/api/projects/${projectId}/deliverables/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateDeliverable(
  projectId: number,
  deliverableId: number,
  payload: {
    expectedVersion: number;
    progressPercent?: number;
    workStatus?: 'planned' | 'in_progress' | 'blocked';
    blockerSummary?: string;
  },
) {
  return apiRequest<Deliverable>(
    `/api/projects/${projectId}/deliverables/${deliverableId}/`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
}

export function submitDeliverable(
  projectId: number,
  deliverableId: number,
  payload: {
    expectedVersion: number;
    description: string;
    evidence: Array<{
      type: 'project_material' | 'task' | 'report' | 'external_url';
      sourceId?: number;
      url?: string;
      label: string;
    }>;
    idempotencyKey: string;
  },
) {
  return apiRequest<DeliverableRevision>(
    `/api/projects/${projectId}/deliverables/${deliverableId}/submit/`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

export function recommendDeliverable(
  projectId: number,
  deliverableId: number,
  payload: {
    revisionId: number;
    recommendation: 'accept' | 'return';
    rationale: string;
    idempotencyKey: string;
  },
) {
  return apiRequest(
    `/api/projects/${projectId}/deliverables/${deliverableId}/recommendations/`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

export function decideDeliverable(
  projectId: number,
  deliverableId: number,
  payload: {
    revisionId: number;
    decision: 'accepted' | 'returned';
    rationale: string;
    expectedVersion: number;
    idempotencyKey: string;
  },
) {
  return apiRequest(
    `/api/projects/${projectId}/deliverables/${deliverableId}/decisions/`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

export type DecisionRecord = {
  id: number;
  projectId: number;
  title: string;
  context: string;
  optionsConsidered: string[];
  outcome: string;
  rationale: string;
  owner: { id: number; displayName: string; role: string };
  effectiveDate: string;
  status: 'current' | 'superseded';
  supersedesId?: number | null;
  supersededById?: number | null;
  publishedBy: { id: number; displayName: string; role: string };
  publishedAt: string;
};

export type DecisionWrite = {
  title: string;
  context: string;
  optionsConsidered: string[];
  outcome: string;
  rationale: string;
  ownerId: number;
  effectiveDate: string;
  links?: Array<{ targetType: string; targetId: number }>;
  idempotencyKey: string;
};

export type RiskRecord = {
  id: number;
  projectId: number;
  title: string;
  description: string;
  sourceType: string;
  likelihood: 'low' | 'medium' | 'high';
  impact: 'low' | 'medium' | 'high';
  severity: 'low' | 'medium' | 'high';
  matrixExplanation: string;
  owner?: { id: number; displayName: string; role: string } | null;
  treatment: string;
  reviewDate?: string | null;
  state: 'raised' | 'open' | 'mitigating' | 'accepted' | 'resolved';
  closureRationale: string;
  version: number;
  raisedBy: { id: number; displayName: string; role: string };
  createdAt: string;
  updatedAt: string;
  revisions: Array<{
    revisionNumber: number;
    previousState: string;
    newState: string;
    severity: string;
    reason: string;
    createdAt: string;
  }>;
};

export function listDecisions(projectId: number, filters: { status?: string; q?: string } = {}) {
  return apiRequest<{ results: DecisionRecord[]; page: { nextCursor: string | null }; canPublish: boolean }>(
    `/api/projects/${projectId}/decisions/${queryString(filters)}`,
  );
}

export function publishDecision(projectId: number, payload: DecisionWrite) {
  return apiRequest<DecisionRecord>(`/api/projects/${projectId}/decisions/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function supersedeDecision(projectId: number, decisionId: number, payload: DecisionWrite) {
  return apiRequest<DecisionRecord>(`/api/projects/${projectId}/decisions/${decisionId}/supersede/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listRisks(
  projectId: number,
  filters: { state?: string; severity?: string; ownerId?: number; q?: string } = {},
) {
  return apiRequest<{ results: RiskRecord[]; page: { nextCursor: string | null }; canRaise: boolean; canTriage: boolean }>(
    `/api/projects/${projectId}/risks/${queryString(filters)}`,
  );
}

export function raiseRisk(
  projectId: number,
  payload: { title: string; description: string; sourceType?: string; sourceId?: number; idempotencyKey: string },
) {
  return apiRequest<RiskRecord>(`/api/projects/${projectId}/risks/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function triageRisk(
  projectId: number,
  riskId: number,
  payload: { expectedVersion: number; likelihood: string; impact: string; ownerId: number; treatment: string; reviewDate: string; reason?: string },
) {
  return apiRequest<RiskRecord>(`/api/projects/${projectId}/risks/${riskId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function transitionRisk(
  projectId: number,
  riskId: number,
  payload: { expectedVersion: number; action: string; reason: string; ownerId?: number; reviewDate?: string; idempotencyKey: string },
) {
  return apiRequest<RiskRecord>(`/api/projects/${projectId}/risks/${riskId}/transitions/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
