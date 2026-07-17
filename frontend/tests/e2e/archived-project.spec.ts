import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('archived project validation controls are available on dashboard', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
  } else {
    let status = 'active';
    await page.route('**/api/projects/1/', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          json: {
            id: 1,
            title: 'Archived validation project',
            description: '',
            status,
            capabilities: projectCapabilities(status),
            memberships: [],
            current_tasks: [],
            pending_reviews: [],
            upcoming_bookings: [],
            activity: [],
          },
        });
        return;
      }
      await route.fulfill({ json: { id: 1, title: 'Archived validation project', status } });
    });
    await page.route('**/api/projects/1/archive/', async (route) => {
      status = 'archived';
      await route.fulfill({ json: { id: 1, title: 'Archived validation project', status, capabilities: projectCapabilities(status) } });
    });
    await page.route('**/api/projects/1/reopen/', async (route) => {
      status = 'active';
      await route.fulfill({ json: { id: 1, title: 'Archived validation project', status, capabilities: projectCapabilities(status) } });
    });
    await page.route('**/api/projects/1/notifications/', async (route) => {
      await route.fulfill({ json: { results: [] } });
    });
  }

  await page.goto('/projects/1');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('heading', { name: fullStackE2E ? 'Graphene Lab' : 'Archived validation project' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Materials');
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Reviews');
  await expect(page.getByRole('button', { name: 'Archive project' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reopen project' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Activity' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Archive project' }).click();
  await expect(page.getByRole('dialog', { name: 'Archive project?' })).toBeVisible();
  await page.getByRole('dialog', { name: 'Archive project?' }).getByRole('button', { name: 'Archive project' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Project status updated' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'Project is archived' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Add task' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Reopen project' })).toBeVisible();
  await page.getByRole('button', { name: 'Reopen project' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Project status updated' })).toBeVisible();
});

function projectCapabilities(status: string) {
  return {
    canManageProject: true,
    canEditProject: true,
    canArchiveProject: status === 'active',
    canReopenProject: status === 'archived',
    canDeleteProject: true,
    canManageMembers: status === 'active',
    canCreateTasks: status === 'active',
    canUpdateTasks: status === 'active',
  };
}
