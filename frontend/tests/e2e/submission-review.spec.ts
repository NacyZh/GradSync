import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
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
  if (fullStackE2E) {
    await loginAs(page, 'student@example.edu');
  }
  await page.goto('/projects/1/drafts');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('heading', { name: 'Submit draft' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Student draft actions' })).toBeVisible();
  await page.getByLabel('Draft title').fill('Paper A');
  await page.getByRole('button', { name: 'Create draft' }).click();
  await expect(page.getByLabel('Create draft').getByRole('status')).toContainText('Draft created');
  await page.getByLabel('Content reference').fill('paper-v1.pdf');
  await page.getByLabel('Summary').fill('Initial submission');
  await page.keyboard.press('Control+Enter');
  await expect(page.getByLabel('Submit draft').getByRole('status')).toContainText('Draft version submitted');

  await page.goto('/projects/1/reports');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await page.getByLabel('Week start').fill('2026-06-22');
  await page.getByLabel('Completed work').fill('Completed experiments');
  await page.getByLabel('Next steps').fill('Write results');
  await page.getByRole('button', { name: 'Submit report' }).click();
  await expect(page.getByLabel('Weekly progress report').getByRole('status')).toContainText('Weekly report submitted');

  await page.goto('/projects/1/reviews');
  if (fullStackE2E) {
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByLabel('Email')).toBeVisible();
    await loginAs(page);
    await page.goto('/projects/1/reviews');
  }
  await expect(page.getByRole('heading', { name: 'Review queue' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('region', { name: 'Submission review' })).toContainText('Week 2026-06-22');
  await expect(page.getByRole('complementary', { name: 'Inline comments' })).toBeVisible();
  await page.getByRole('listitem').filter({ hasText: 'Week 2026-06-22' }).getByLabel('Review status').selectOption('reviewed');
  await expect(page.getByLabel('Report reviews').getByRole('status')).toContainText('Review status updated');
});
