import { expect, test } from '@playwright/test';

import {
  fulfillJson,
  fullStackE2E,
  loginAs,
  mockAuthenticatedApi,
} from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('advisor opens bounded milestone and deliverable execution workspace', async ({
  page,
}) => {
  if (!fullStackE2E) {
    await page.route('**/api/projects/1/execution-summary/', (route) =>
      fulfillJson(route, {
        projectId: 1,
        milestoneCounts: { in_progress: 1 },
        deliverableCounts: { under_review: 1 },
        riskCounts: {},
        pendingReviews: 1,
        missingReports: 0,
        unresolvedActions: 1,
        upcoming: [],
        capabilities: {
          canManageMilestones: true,
          canManageDeliverables: true,
          canSubmitAssignedDeliverables: false,
          canRecommendDeliverables: true,
          canDecideDeliverables: true,
          canPublishDecisions: true,
          canRaiseRisks: true,
          canTriageRisks: true,
        },
      }),
    );
    await page.route('**/api/projects/1/milestones/**', (route) =>
      fulfillJson(route, {
        results: [
          {
            id: 1,
            projectId: 1,
            title: 'Validated prototype',
            description: 'Reproducible output.',
            targetDate: '2026-08-20',
            ownerIds: [12],
            order: 0,
            status: 'in_progress',
            version: 1,
            requiredDeliverables: 1,
            acceptedDeliverables: 0,
            completedAt: null,
            archivedAt: null,
            createdAt: '2026-07-28T00:00:00Z',
            updatedAt: '2026-07-28T00:00:00Z',
          },
        ],
        page: { nextCursor: null },
        capabilities: {},
      }),
    );
    await page.route('**/api/projects/1/deliverables/**', (route) =>
      fulfillJson(route, {
        results: [
          {
            id: 4,
            projectId: 1,
            milestoneId: 1,
            title: 'Prototype package',
            description: '',
            acceptanceCriteria: 'Runs from a clean environment.',
            dueDate: '2026-08-18',
            required: true,
            reviewerRequired: true,
            status: 'under_review',
            progressPercent: 45,
            blockerSummary: '',
            assignees: [{ id: 12, name: 'Student One' }],
            taskIds: [],
            version: 2,
            acceptedRevisionId: null,
            revisions: [],
            capabilities: {
              canManageMilestones: true,
              canManageDeliverables: true,
              canSubmitAssignedDeliverables: false,
              canRecommendDeliverables: true,
              canDecideDeliverables: true,
              canPublishDecisions: true,
              canRaiseRisks: true,
              canTriageRisks: true,
            },
          },
        ],
        page: { nextCursor: null },
        capabilities: {},
      }),
    );
    await page.route('**/api/projects/1/materials/**', (route) =>
      fulfillJson(route, { count: 0, results: [] }),
    );
  } else {
    await loginAs(page);
  }
  await page.goto('/projects/1/execution');
  await expect(page.getByRole('heading', { name: 'Project execution' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText(
    'Execution',
  );
  if (!fullStackE2E) {
    await expect(page.getByLabel('Milestone list')).toContainText('Validated prototype');
    await page.getByRole('tab', { name: 'Deliverables' }).click();
    await expect(page.getByLabel('Deliverable list')).toContainText('Prototype package');
    await expect(page.getByText('Runs from a clean environment.')).toBeVisible();
  }
});
