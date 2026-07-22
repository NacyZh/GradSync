import { expect, test } from '@playwright/test';

import {
  fulfillJson,
  fullStackE2E,
  mockAuthenticatedApi,
  mockUnavailableTokenRefresh,
} from './api-mocks';

test.beforeEach(() => {
  test.skip(fullStackE2E, 'mock-owned registration responses are covered by the mocked Playwright stage');
});

test('registration and role approval flow is reachable', async ({ page }) => {
  await page.route('**/api/accounts/register/', async (route) => {
    await fulfillJson(route, { email: 'student@example.com', status: 'pending_email_verification', requestedRole: 'student' }, 202);
  });
  await page.route('**/api/accounts/verify-email/', async (route) => {
    await fulfillJson(route, { id: 1, email: 'student@example.com', name: 'Student', global_role: 'student', status: 'active' });
  });

  await page.goto('/register');
  await page.getByLabel('Email').fill('student@example.com');
  await page.getByLabel('Full name').fill('Student Example');
  await page.getByLabel('Workspace nickname').fill('Student');
  await page.getByLabel('Password', { exact: true }).fill('StrongPass1!');
  await page.getByLabel('Confirm password').fill('StrongPass1!');
  await page.getByRole('button', { name: 'Register' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Verification email sent' }).first()).toBeVisible();
  await page.getByLabel('Verification code').fill('123456');
  await page.getByRole('button', { name: 'Verify email' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Email verified' }).first()).toBeVisible();
});

test('administrator can review role activation requests', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await mockUnavailableTokenRefresh(page);
  await page.route('**/api/accounts/me/', async (route) => {
    await fulfillJson(route, { id: 10, email: 'admin@example.edu', name: 'Admin One', global_role: 'admin', status: 'active' });
  });
  await page.route('**/api/accounts/admin/role-activations/', async (route) => {
    await fulfillJson(route, [{ id: 1, status: 'pending', requestedRole: 'teacher', activationSource: 'administrator_approval', createdAt: '2026-07-03T00:00:00Z', user: { id: 2, email: 'teacher@example.edu', name: 'Teacher One', global_role: 'advisor', status: 'pending_role_activation' } }]);
  });
  await page.route('**/api/accounts/admin/role-activations/1/', async (route) => {
    await fulfillJson(route, { id: 1, status: 'approved', requestedRole: 'teacher', user: { id: 2, email: 'teacher@example.edu', name: 'Teacher One', global_role: 'advisor', status: 'active' } });
  });

  await page.goto('/admin/role-activations');
  await expect(page.getByText('teacher@example.edu')).toBeVisible();
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Activation updated' }).first()).toBeVisible();
});
