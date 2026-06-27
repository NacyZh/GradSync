import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.route('**/api/projects/1/drafts/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 51, title: 'Paper A', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: 51, title: 'Paper A', status: 'active' }] });
  });
  await page.route('**/api/projects/1/drafts/51/versions/', async (route) => {
    await fulfillJson(route, { id: 61, version_number: 1, review_status: 'pending_review', content_reference: 'paper-v1.pdf' }, 201);
  });
  await page.route('**/api/projects/1/reports/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 71, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', review_status: 'pending_review' }, 201);
      return;
    }
    await fulfillJson(route, {
      results: [{ id: 71, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', review_status: 'pending_review' }],
    });
  });
  await page.route('**/api/projects/1/reports/71/review/', async (route) => {
    await fulfillJson(route, { id: 71, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', review_status: 'reviewed' });
  });
});

test('student submits draft/report and advisor updates review status', async ({ page }) => {
  await page.goto('/projects/1/drafts');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('heading', { name: 'Submit draft' })).toBeVisible();
  await page.getByLabel('Draft title').fill('Paper A');
  await page.getByRole('button', { name: 'Create draft' }).click();
  await expect(page.getByText('Draft created')).toBeVisible();
  await page.getByLabel('Content reference').fill('paper-v1.pdf');
  await page.getByLabel('Summary').fill('Initial submission');
  await page.getByRole('button', { name: 'Submit draft' }).click();
  await expect(page.getByText('Draft version submitted')).toBeVisible();

  await page.goto('/projects/1/reports');
  await page.getByLabel('Week start').fill('2026-06-22');
  await page.getByLabel('Completed work').fill('Completed experiments');
  await page.getByLabel('Next steps').fill('Write results');
  await page.getByRole('button', { name: 'Submit report' }).click();
  await expect(page.getByText('Weekly report submitted')).toBeVisible();

  await page.goto('/projects/1/reviews');
  await expect(page.getByRole('heading', { name: 'Review queue' })).toBeVisible();
  await page.getByLabel('Review status').selectOption('reviewed');
  await expect(page.getByText('Review status updated')).toBeVisible();
});
