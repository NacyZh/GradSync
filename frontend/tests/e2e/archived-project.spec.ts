import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('archived project validation controls are available on dashboard', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let projectPath = '/projects/1';
  let projectTitle = 'Archived validation project';
  if (fullStackE2E) {
    await loginAs(page);
    projectTitle = 'Archive lifecycle project';
    await page.goto('/projects/new');
    await page.getByLabel('Project title').fill(projectTitle);
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page).toHaveURL(/\/projects\/\d+$/);
    projectPath = new URL(page.url()).pathname;
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
      await route.fulfill({
        json: {
          projectId: 1,
          status,
          archiveVersion: 1,
          archivedAt: new Date().toISOString(),
          checklist: {},
        },
      });
    });
    await page.route('**/api/projects/1/closeout/', async (route) => {
      await route.fulfill({
        json: {
          projectId: 1,
          ready: true,
          checks: [
            'incompleteTasks',
            'pendingReports',
            'pendingMaterialPermissions',
            'unacceptedRequiredDeliverables',
            'unreturnedResources',
            'openBookings',
          ].map((key) => ({ key, count: 0, severity: 'clear', sample: [] })),
          latestCloseout: null,
        },
      });
    });
    await page.route('**/api/projects/1/reopen/', async (route) => {
      status = 'active';
      await route.fulfill({ json: { id: 1, title: 'Archived validation project', status, capabilities: projectCapabilities(status) } });
    });
    await page.route('**/api/projects/1/notifications/', async (route) => {
      await route.fulfill({ json: { results: [] } });
    });
  }

  await page.goto(projectPath);
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('heading', { name: projectTitle })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Materials');
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Reviews');
  await expect(page.getByRole('button', { name: 'Archive project' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reopen project' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Activity' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Archive project' }).click();
  const closeout = page.getByRole('dialog', { name: 'Archive project?' });
  await expect(closeout).toBeVisible();
  for (const label of [
    'Cancel all remaining tasks',
    'Close pending reports as unresolved',
    'Cancel pending and future bookings',
  ]) {
    const checkbox = closeout.getByRole('checkbox', { name: label });
    if (await checkbox.count()) await checkbox.check();
  }
  await closeout.getByRole('checkbox', { name: 'I reviewed final material visibility and access' }).check();
  await closeout.getByRole('checkbox', { name: 'Accepted deliverables and evidence form the final outcomes package' }).check();
  await closeout.getByRole('button', { name: 'Complete closeout and archive' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Project closeout completed' }).first()).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'Project is archived' }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Add task' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Reopen project' })).toBeVisible();
  await page.getByRole('button', { name: 'Reopen project' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Project reopened' }).first()).toBeVisible();
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
