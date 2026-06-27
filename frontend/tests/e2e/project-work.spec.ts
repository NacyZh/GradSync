import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('advisor can create a project and dashboard shows isolated project activity', async ({ page }) => {
  await page.route('**/api/projects/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 2, title: 'Quantum Thesis', description: '', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [] });
  });

  await page.goto('/projects/new');
  await expect(page.getByRole('heading', { name: 'Create project' })).toBeVisible();
  await page.getByLabel('Project title').fill('Quantum Thesis');
  await page.getByLabel('Student IDs').fill('12,13');
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('Created project Quantum Thesis')).toBeVisible();

  await page.goto('/projects/1');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('region', { name: 'Current tasks' })).toContainText('1 active tasks');
  await expect(page.getByRole('region', { name: 'Pending reviews' })).toContainText('1 pending reviews');
  await expect(page.getByRole('region', { name: 'Activity' })).toContainText('Pending review reminder');
});
