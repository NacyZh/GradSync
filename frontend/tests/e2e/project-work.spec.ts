import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('advisor can create a project and dashboard shows isolated project activity', async ({ page }) => {
  if (!fullStackE2E) {
    await page.route('**/api/projects/', async (route) => {
      if (route.request().method() === 'POST') {
        await fulfillJson(route, { id: 2, title: 'Quantum Thesis', description: '', status: 'active' }, 201);
        return;
      }
      await fulfillJson(route, { results: [] });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/projects/new');
  await expect(page.getByRole('heading', { name: 'Create project' })).toBeVisible();
  await page.getByLabel('Project title').fill('Quantum Thesis');
  await page.getByLabel('Student IDs').fill('12,13');
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('Created project Quantum Thesis')).toBeVisible();

  await page.goto('/projects/1');
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('region', { name: 'Current tasks' })).toContainText('Analyze sample');
  await page.getByRole('link', { name: 'Update status' }).nth(1).click();
  await expect(page.getByRole('region', { name: 'Task details' })).toContainText('Priority: high');
  await expect(page.getByRole('region', { name: 'Pending reviews' })).toContainText(/Review progress_report #\d+/);
  await expect(page.getByRole('region', { name: 'Activity' })).toContainText('Pending review reminder');
  await page.getByLabel('Task status').selectOption('completed');
  await expect(page.getByRole('region', { name: 'Current tasks' }).getByRole('status')).toContainText('Task status updated');

  if (fullStackE2E) {
    await page.getByRole('button', { name: 'Sign out' }).click();
    await loginAs(page, 'student@example.edu');
    await page.goto('/projects/2');
    await expect(page).toHaveURL(/\/login|\/projects\/2/);
    await expect(page.getByText('Quantum Thesis')).not.toBeVisible();
  }
});
