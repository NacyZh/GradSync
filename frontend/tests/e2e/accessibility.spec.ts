import { expect, test } from '@playwright/test';

import {
  currentUser,
  fulfillJson,
  fullStackE2E,
  loginAs,
  mockAccountSecurity,
  mockAuditConsole,
  mockAuthenticatedApi,
} from './api-mocks';

test('main application landmarks are present', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await mockAccountSecurity(page);
  await mockAuditConsole(page);
  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary workspace' })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Search' })).toBeVisible();
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

test('access governance workspaces expose keyboard-operable controls', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await mockAccountSecurity(page);
  await mockAuditConsole(page);
  if (!fullStackE2E) {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, { ...currentUser, global_role: 'admin' });
    });
  } else {
    await loginAs(page, 'admin@gradsync.local');
  }

  await page.goto('/profile');
  await expect(page.getByRole('heading', { name: 'Security', exact: true })).toBeVisible();
  await page.getByLabel('New email').focus();
  await expect(page.getByLabel('New email')).toBeFocused();

  await page.goto('/admin/audit');
  const auditFilters = page.getByRole('region', { name: 'Audit filters' });
  await expect(auditFilters).toBeVisible();
  await auditFilters.getByLabel('Search').focus();
  await page.keyboard.type('project');
  await expect(page).toHaveURL(/q=project/);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus-visible').first()).toBeVisible();
});
