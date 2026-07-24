import { expect, test } from '@playwright/test';

import { mockAccountSecurity, mockUnauthenticated } from './api-mocks';

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
