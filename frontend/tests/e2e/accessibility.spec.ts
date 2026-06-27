import { expect, test } from '@playwright/test';

import { mockAuthenticatedApi } from './api-mocks';

test('main application landmarks are present', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.goto('/');
  await expect(page.locator('main')).toBeVisible();
  await page.goto('/projects/new');
  await expect(page.getByLabel('Project title')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create' })).toBeVisible();
  await page.goto('/projects/1/resources');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toBeVisible();
  await expect(page.getByLabel('Availability start')).toBeVisible();
});
