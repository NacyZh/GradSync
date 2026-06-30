import { expect, test } from '@playwright/test';

import { fulfillJson } from './api-mocks';

test.describe('role workspaces', () => {
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

    await page.goto('/');
    await expect(page.getByText('Admin User')).toBeVisible();
    await expect(page.getByText('admin')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Accounts' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'New Project' })).toBeVisible();

    await page.getByRole('link', { name: 'Manage accounts' }).click();
    await expect(page).toHaveURL('/admin/accounts');
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
    await expect(page.getByRole('link', { name: 'New Project' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Accounts' })).not.toBeVisible();

    // Advisor cannot access admin routes.
    await page.goto('/admin/accounts');
    await expect(page).toHaveURL('/');
  });

  test('student cannot see project creation or account admin', async ({ page }) => {
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
    await expect(page.getByRole('link', { name: 'Resources' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'New Project' })).not.toBeVisible();
    await expect(page.getByRole('link', { name: 'Accounts' })).not.toBeVisible();

    // Student cannot access project creation.
    await page.goto('/projects/new');
    await expect(page).toHaveURL('/');
  });
});
