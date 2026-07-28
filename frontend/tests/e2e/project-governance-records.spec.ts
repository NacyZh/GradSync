import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('decision and risk registers use bounded list detail governance views', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page);
  } else {
    await page.route('**/api/projects/1/execution-summary/', (route) =>
      fulfillJson(route, {
        projectId: 1,
        milestoneCounts: {},
        deliverableCounts: {},
        riskCounts: { high: 1 },
        pendingReviews: 0,
        missingReports: 0,
        unresolvedActions: 0,
        upcoming: [],
        capabilities: {
          canManageMilestones: true,
          canManageDeliverables: true,
          canPublishDecisions: true,
          canRaiseRisks: true,
          canTriageRisks: true,
        },
      }),
    );
    await page.route('**/api/projects/1/milestones/**', (route) =>
      fulfillJson(route, { results: [], page: { nextCursor: null } }),
    );
    await page.route('**/api/projects/1/deliverables/**', (route) =>
      fulfillJson(route, { results: [], page: { nextCursor: null } }),
    );
    await page.route('**/api/projects/1/materials/**', (route) =>
      fulfillJson(route, { results: [] }),
    );
    await page.route('**/api/projects/1/decisions/**', (route) =>
      fulfillJson(route, {
        results: [{
          id: 1,
          projectId: 1,
          title: 'Adopt protocol',
          context: 'Protocol context',
          optionsConsidered: ['A', 'B'],
          outcome: 'A',
          rationale: 'Validated',
          owner: { id: 1, displayName: 'Advisor', role: 'advisor' },
          effectiveDate: '2026-07-28',
          status: 'current',
          publishedBy: { id: 1, displayName: 'Advisor', role: 'advisor' },
          publishedAt: '2026-07-28T00:00:00Z',
        }],
        page: { nextCursor: null },
        canPublish: true,
      }),
    );
    await page.route('**/api/projects/1/risks/**', (route) =>
      fulfillJson(route, {
        results: [{
          id: 2,
          projectId: 1,
          title: 'Recruitment delay',
          description: 'Behind plan',
          sourceType: 'manual',
          likelihood: 'medium',
          impact: 'high',
          severity: 'high',
          matrixExplanation: 'medium likelihood and high impact produce high severity.',
          owner: null,
          treatment: '',
          reviewDate: null,
          state: 'raised',
          closureRationale: '',
          version: 1,
          raisedBy: { id: 2, displayName: 'Student', role: 'student' },
          createdAt: '2026-07-28T00:00:00Z',
          updatedAt: '2026-07-28T00:00:00Z',
          revisions: [],
        }],
        page: { nextCursor: null },
        canRaise: true,
        canTriage: true,
      }),
    );
  }
  await page.goto('/projects/1/execution');
  await page.getByRole('tab', { name: 'Decisions' }).click();
  if (!fullStackE2E) {
    await expect(page.getByText('Protocol context')).toBeVisible();
    await page.getByRole('tab', { name: 'Risks' }).click();
    await expect(page.getByText(/medium likelihood and high impact/)).toBeVisible();
    for (const width of [390, 900, 1440]) {
      await page.setViewportSize({ width, height: 950 });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('tab', { name: 'Decisions' }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Risks' })).toBeFocused();
    await page.setViewportSize({ width: 900, height: 950 });
    await page.evaluate(() => {
      document.documentElement.style.zoom = '2';
    });
    await expect(page.getByRole('heading', { name: 'Risk register' })).toBeVisible();
  } else {
    await expect(page.getByRole('heading', { name: 'Decision register' })).toBeVisible();
  }
});
