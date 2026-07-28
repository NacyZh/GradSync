import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('reports expose period history template and transparent analytics views', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page);
  } else {
    await page.route('**/api/projects/1/report-templates/', (route) =>
      fulfillJson(route, {
        results: [{
          id: 1,
          templateId: 1,
          projectId: 1,
          name: 'Weekly progress',
          versionNumber: 1,
          status: 'published',
          version: 2,
          fields: [{
            id: 10,
            key: 'progress_percent',
            labelEn: 'Progress',
            labelZh: '进度',
            fieldType: 'percentage',
            required: true,
            order: 0,
            options: [],
            analyticsEnabled: true,
          }],
        }],
        capabilities: {
          canEditTemplate: true,
          canPublishTemplate: true,
          canSubmitReport: false,
          canViewAnalytics: true,
          canExportAnalytics: true,
        },
      }),
    );
    await page.route('**/api/projects/1/reporting-periods/**', (route) =>
      fulfillJson(route, {
        results: [{
          id: 2,
          projectId: 1,
          startsOn: '2026-07-27',
          endsOn: '2026-08-03',
          deadlineAt: '2026-08-02T18:00:00Z',
          templateVersionId: 1,
          state: 'open',
        }],
        page: { nextCursor: null },
      }),
    );
    await page.route('**/api/projects/1/report-analytics/**', (route) =>
      fulfillJson(route, {
        projectId: 1,
        from: '2026-07-27',
        to: '2026-08-03',
        submissionCounts: { expected: 1, onTime: 1, late: 0, missing: 0 },
        metricSeries: [{
          key: 'progress_percent',
          labelEn: 'Progress',
          labelZh: '进度',
          value: 60,
          unit: 'percent',
          population: 1,
          missing: 0,
          sourceReportIds: [3],
        }],
      }),
    );
  }
  await page.goto('/projects/1/reports');
  await expect(page.getByRole('tab', { name: 'Periods' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'History' })).toBeVisible();
  if (!fullStackE2E) {
    await page.getByRole('tab', { name: 'Analytics' }).click();
    await expect(page.getByText('Metrics are descriptive and never produce rankings or composite scores.')).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Metric' })).toBeVisible();
  }
});
