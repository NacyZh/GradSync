import { expect, test, type Page } from '@playwright/test';

import { currentUser, fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

const studentUser = {
  id: 12,
  email: 'student@example.edu',
  name: 'Student One',
  global_role: 'student',
  status: 'active',
};

async function openReportsAfterInitialLoad(page: Page) {
  const reportsLoaded = page.waitForResponse((response) =>
    response.request().method() === 'GET'
      && response.url().includes('/api/projects/1/reports/'),
  );
  await page.goto('/projects/1/reports');
  await reportsLoaded;
}

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (!fullStackE2E) {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, studentUser);
    });
  }
  if (fullStackE2E) {
    return;
  }
  let reportRevision = 0;
  await page.route('**/api/projects/1/reports/', async (route) => {
    if (route.request().method() === 'POST') {
      reportRevision += 1;
      await fulfillJson(route, { id: 70 + reportRevision, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', revision_number: reportRevision, review_status: 'pending_review' }, 201);
      return;
    }
    await fulfillJson(route, {
      results: reportRevision
        ? [{ id: 70 + reportRevision, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', revision_number: reportRevision, review_status: 'pending_review' }]
        : [],
    });
  });
  await page.route('**/api/projects/1/reports/71/review/', async (route) => {
    await fulfillJson(route, { id: 71, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', revision_number: 1, review_status: 'needs_revision' });
  });
  await page.route('**/api/projects/1/reports/72/review/', async (route) => {
    await fulfillJson(route, { id: 72, report_week_start: '2026-06-22', completed_work: 'Done', next_steps: 'Next', revision_number: 2, review_status: 'reviewed' });
  });
});

test('student submits report revision and advisor updates review status', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'student@example.edu');
  }
  await openReportsAfterInitialLoad(page);
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Weekly progress report' })).toBeVisible();
  await page.getByLabel('Week start').fill('2026-06-22');
  await page.getByLabel('Completed work').fill('Completed experiments');
  await page.getByLabel('Next steps').fill('Write results');
  await page.getByRole('button', { name: 'Submit report' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Weekly report submitted' }).first()).toBeVisible();

  await page.goto('/projects/1/reviews');
  if (fullStackE2E) {
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByLabel('Email')).toBeVisible();
    await loginAs(page);
    await page.goto('/projects/1/reviews');
  } else {
    await page.unroute('**/api/accounts/me/');
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, currentUser);
    });
    await page.goto('/projects/1/reviews');
  }
  await expect(page.getByRole('heading', { name: 'Review queue' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Review queue list' })).toContainText('Week 2026-06-22');
  await page.getByRole('button', { name: /Week 2026-06-22/ }).click();
  await expect(page.getByRole('region', { name: 'Submission review' })).toContainText('Week 2026-06-22');
  await expect(page.getByRole('complementary', { name: 'Inline comments' })).toBeVisible();
  await page.getByRole('region', { name: 'Submission review' }).getByLabel('Review status').selectOption('needs_revision');
  await expect(page.getByRole('status').filter({ hasText: 'Review status updated' }).first()).toBeVisible();

  if (fullStackE2E) {
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByLabel('Email')).toBeVisible();
    await loginAs(page, 'student@example.edu');
  } else {
    await page.unroute('**/api/accounts/me/');
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, studentUser);
    });
  }
  await openReportsAfterInitialLoad(page);
  await page.getByLabel('Week start').fill('2026-06-22');
  await page.getByLabel('Completed work').fill('Completed experiments revised');
  await page.getByLabel('Next steps').fill('Write results');
  await page.getByRole('button', { name: 'Submit report' }).click();
  await expect(page.getByText(/Revision 2/)).toBeVisible();

  if (fullStackE2E) {
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByLabel('Email')).toBeVisible();
    await loginAs(page);
  } else {
    await page.unroute('**/api/accounts/me/');
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, currentUser);
    });
  }
  await page.goto('/projects/1/reviews');
  await page.getByRole('button', { name: /Revision 2/ }).click();
  await page.getByRole('region', { name: 'Submission review' }).getByLabel('Review status').selectOption('reviewed');
  await expect(page.getByRole('status').filter({ hasText: 'Review status updated' }).first()).toBeVisible();
});
