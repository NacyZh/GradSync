import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('archived project validation controls are available on dashboard', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  } else {
    await page.route('**/api/projects/1/', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          json: {
            id: 1,
            title: 'Archived validation project',
            description: '',
            status: 'active',
            memberships: [],
            current_tasks: [],
            pending_reviews: [],
            upcoming_bookings: [],
            activity: [],
          },
        });
        return;
      }
      await route.fulfill({ json: { id: 1, title: 'Archived validation project', status: 'archived' } });
    });
    await page.route('**/api/projects/1/notifications/', async (route) => {
      await route.fulfill({ json: { results: [] } });
    });
  }

  await page.goto('/projects/1');
  await expect(page.getByRole('button', { name: 'Archive project' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reopen project' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Activity' })).toBeVisible();
});
