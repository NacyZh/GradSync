import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('main application landmarks are present', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary workspace' })).toBeVisible();
  await expect(page.getByRole('searchbox').or(page.getByPlaceholder('Search projects, tasks, reviews'))).toBeVisible();
  await page.getByRole('button', { name: 'Switch to dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus-visible').first()).toBeVisible();
  await page.goto('/projects/new');
  await expect(page.getByRole('main')).toContainText('Create project');
  await expect(page.getByLabel('Project title')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create' })).toBeVisible();
  await page.goto('/projects/1/resources');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toHaveCount(0);
  await expect(page.getByLabel('Availability start')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resource filters' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toBeVisible();
  await page.setViewportSize({ width: 900, height: 700 });
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
});

test('project dashboard member focus remains stable during refresh window', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  }

  await page.goto('/projects/1');
  const selector = page.getByLabel('Student nickname');
  await selector.focus();
  await expect(selector).toBeFocused();
  await page.waitForTimeout(5200);
  await expect(selector).toBeFocused();
});

test('dashboard calendar supports keyboard views, filters, and schedule dialog', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/');
  const calendar = page.getByRole('region', { name: 'Dashboard calendar' });
  await expect(calendar).toBeVisible();
  await calendar.getByRole('button', { name: 'Week', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(calendar.getByRole('button', { name: 'Week', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await calendar.getByRole('button', { name: /Filter calendar sources/ }).click();
  await expect(page.getByRole('group', { name: 'Calendar sources' })).toBeVisible();
  await page.keyboard.press('Escape');
  await calendar.getByRole('button', { name: 'New schedule' }).click();
  const dialog = page.getByRole('dialog', { name: /schedule/i });
  await expect(dialog.locator(':focus-visible')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
});
