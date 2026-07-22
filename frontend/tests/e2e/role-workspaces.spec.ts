import { expect, test } from '@playwright/test';

import { fulfillJson, mockUnavailableTokenRefresh } from './api-mocks';

test.describe('role workspaces', () => {
  test.beforeEach(async ({ page }) => {
    await mockUnavailableTokenRefresh(page);
  });

  test('admin sees account management and can navigate', async ({ page }) => {
    const adminUser = {
      id: 1,
      email: 'admin@gradsync.local',
      name: 'Admin User',
      global_role: 'admin',
      status: 'active' as const,
    };

    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, adminUser);
    });
    await page.route('**/api/accounts/logout/', async (route) => {
      await fulfillJson(route, {}, 204);
    });
    await page.route('**/api/projects/', async (route) => {
      await fulfillJson(route, { results: [] });
    });
    await page.route('**/api/accounts/?**', async (route) => {
      await fulfillJson(route, { results: [adminUser], next: null, previous: null });
    });

    await page.goto('/');
    await expect(page.getByText('Admin User')).toBeVisible();
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Role workspace' })).toContainText('Administration');
    await expect(page.getByRole('banner').getByText('admin', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Team' })).toBeVisible();
    await expect(
      page.getByLabel('Primary workspace').getByRole('link', { name: 'Projects' })
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Open notifications' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Switch to dark theme' })).toBeVisible();

    await page.getByRole('link', { name: 'Team' }).click();
    await expect(page).toHaveURL('/admin/accounts');
    await expect(page.getByRole('heading', { name: 'Account administration' })).toBeVisible();
  });

  test('advisor sees project management but no account admin', async ({ page }) => {
    const advisorUser = {
      id: 2,
      email: 'advisor@example.edu',
      name: 'Advisor User',
      global_role: 'advisor',
      status: 'active' as const,
    };

    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, advisorUser);
    });
    await page.route('**/api/accounts/logout/', async (route) => {
      await fulfillJson(route, {}, 204);
    });
    await page.route('**/api/projects/', async (route) => {
      await fulfillJson(route, { results: [] });
    });

    await page.goto('/');
    await expect(page.getByText('Advisor User')).toBeVisible();
    await expect(page.getByRole('region', { name: 'Role workspace' })).toContainText('Advisor review');
    await expect(
      page.getByLabel('Primary workspace').getByRole('link', { name: 'Projects' })
    ).toBeVisible();
    await expect(page.getByRole('link', { name: 'Team' })).not.toBeVisible();

    // Advisor cannot access admin routes.
    await page.goto('/admin/accounts');
    await expect(page).toHaveURL('/');
  });

  test('student can enter projects but cannot create projects or access account admin', async ({ page }) => {
    const studentUser = {
      id: 3,
      email: 'student@example.edu',
      name: 'Student User',
      global_role: 'student',
      status: 'active' as const,
    };

    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, studentUser);
    });
    await page.route('**/api/accounts/logout/', async (route) => {
      await fulfillJson(route, {}, 204);
    });
    await page.route('**/api/projects/', async (route) => {
      await fulfillJson(route, { results: [] });
    });

    await page.goto('/');
    await expect(page.getByText('Student User')).toBeVisible();
    await expect(page.getByRole('region', { name: 'Role workspace' })).toContainText('Student work');
    await expect(page.getByLabel('Primary workspace').getByRole('link', { name: 'Resources' })).toBeVisible();
    await expect(page.getByLabel('Primary workspace').getByRole('link', { name: 'Projects' })).toHaveAttribute('href', '/projects');
    await expect(page.getByRole('link', { name: 'Team' })).not.toBeVisible();

    // Student cannot access project creation.
    await page.goto('/projects/new');
    await expect(page).toHaveURL('/');
  });
});
