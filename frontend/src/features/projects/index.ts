export {
  listProjects,
  getProject,
  searchEligibleTeachers,
  type CollaboratorRole,
  type TeacherOption,
} from './api';
export {
  getExecutionSummary,
  listMilestones,
  listDeliverables,
  type Deliverable,
  type DeliverableRevision,
  type ExecutionCapabilities,
  type ExecutionSummary,
  type Milestone,
} from './executionApi';
export { DeliverableDetail } from './DeliverableDetail';

export const projectExecutionQueryKeys = (projectId: number) => [
  ['project-execution', projectId],
  ['project-milestones', projectId],
  ['project-deliverables', projectId],
  ['project-report-templates', projectId],
  ['project-report-analytics', projectId],
  ['project-decisions', projectId],
  ['project-risks', projectId],
  ['project-notification-policy', projectId],
] as const;
