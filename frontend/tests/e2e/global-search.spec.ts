import { expect, test } from '@playwright/test';

import {
  fulfillJson,
  fullStackE2E,
  loginAs,
  mockAuthenticatedApi,
} from './api-mocks';

test('global search finds a permitted task through the unified backend endpoint', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  } else {
    await page.route('**/api/search/?**', async (route) => {
      await fulfillJson(route, {
        query: 'analyze sample',
        results: [{
          id: 'task:11',
          type: 'task',
          title: 'Analyze sample',
          context: 'Graphene Lab · In progress',
          path: '/projects/1',
          projectId: 1,
        }],
        counts: {
          project: 0,
          task: 1,
          report: 0,
          paper: 0,
          document: 0,
          code: 0,
          member: 0,
        },
      });
    });
  }

  await page.goto('/');
  await page.getByRole('combobox', { name: 'Search' }).fill('Analyze sample');
  const taskResult = page.getByRole('option', { name: /Analyze sample.*Task.*Graphene Lab/ });
  await expect(taskResult).toBeVisible();
  await taskResult.click();
  await expect(page).toHaveURL(/\/projects\/1$/);
});
