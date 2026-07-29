import { expect, test } from '@playwright/test';

import {
  fullStackE2E,
  loginAs,
  mockAccountSecurity,
  mockAuthenticatedApi,
  mockUnauthenticated,
} from './api-mocks';

test('password recovery remains public and non-enumerating', async ({ page }) => {
  await mockUnauthenticated(page);
  await mockAccountSecurity(page);
  await page.goto('/login');
  await page.getByRole('link', { name: 'Forgot password' }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByLabel('Email').fill('unknown@example.com');
  await page.getByRole('button', { name: 'Send recovery instructions' }).click();
  await expect(
    page.getByText('If the account is eligible, recovery instructions will be sent.'),
  ).toBeVisible();
});

test('profile exposes email change and account session controls', async ({ page }) => {
  await mockAuthenticatedApi(page);
  await mockAccountSecurity(page);
  if (fullStackE2E) await loginAs(page);

  await page.goto('/profile');

  await expect(page.getByRole('heading', { name: 'Security' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sign-in email' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Request email change' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Account sessions' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign out other devices' })).toBeVisible();
});
