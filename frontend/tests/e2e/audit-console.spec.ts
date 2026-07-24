import { expect, test } from '@playwright/test';

import {
  currentUser,
  fulfillJson,
  fullStackE2E,
  mockAuditConsole,
  mockAuthenticatedApi,
} from './api-mocks';

test('administrator inspects redacted audit evidence responsively', async ({ page }) => {
  test.skip(fullStackE2E, 'mock-owned responsive audit fixture is covered in the mocked stage');
  await mockAuthenticatedApi(page);
  await page.route('**/api/accounts/me/', async (route) => {
    await fulfillJson(route, { ...currentUser, global_role: 'admin' });
  });
  await mockAuditConsole(page);

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 1440, height: 950 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/admin/audit');
    await expect(page.getByRole('heading', { name: 'Audit console' })).toBeVisible();
    await expect(page.getByText('Ownership transferred').first()).toBeVisible();
    await expect(page.getByRole('region', { name: 'Audit event detail' })).toBeVisible();
    await expect(page.getByText('Administrator')).toBeVisible();
  }
});
