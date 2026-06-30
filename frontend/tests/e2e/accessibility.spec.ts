import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('main application landmarks are present', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/');
  await expect(page.locator('main')).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Switch to dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.goto('/projects/new');
  await expect(page.getByLabel('Project title')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create' })).toBeVisible();
  await page.goto('/projects/1/resources');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toBeVisible();
  await expect(page.getByLabel('Availability start')).toBeVisible();
  await page.setViewportSize({ width: 900, height: 700 });
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
});
