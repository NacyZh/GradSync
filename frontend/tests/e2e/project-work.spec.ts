import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('advisor can enter projects from primary navigation', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page);
  }

  await page.goto('/');
  await page.getByRole('link', { name: 'Projects' }).first().click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
  await expect(page.getByRole('link', { name: /New project/ })).toBeVisible();
  if (!fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Visible projects' })).toContainText('Graphene Lab');
    await expect(page.getByRole('link', { name: 'Open', exact: true })).toHaveAttribute('href', '/projects/1');
  }
});

test('advisor can create a project and dashboard shows isolated project work', async ({ page }) => {
  if (!fullStackE2E) {
    await page.route('**/api/projects/', async (route) => {
      if (route.request().method() === 'POST') {
        await fulfillJson(route, { id: 2, title: 'Quantum Thesis', description: '', status: 'active' }, 201);
        return;
      }
      await fulfillJson(route, { results: [] });
    });
    await page.route('**/api/projects/2/', async (route) => {
      await fulfillJson(route, {
        id: 2,
        title: 'Quantum Thesis',
        description: '',
        status: 'active',
        capabilities: {
          canManageProject: true,
          canEditProject: true,
          canArchiveProject: true,
          canReopenProject: false,
          canDeleteProject: true,
          canManageMembers: true,
          canCreateTasks: true,
          canUpdateTasks: true,
          deleteDisabledReason: '',
        },
        memberships: [],
        current_tasks: [],
        pending_reviews: [],
        upcoming_bookings: [],
        activity: [],
      });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/projects/new');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create project' })).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Project setup guidance' })).toContainText('Project-scoped by default');
  await page.getByLabel('Project title').fill('Quantum Thesis');
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page).toHaveURL(/\/projects\/\d+$/);
  await expect(page.getByRole('heading', { name: 'Quantum Thesis' })).toBeVisible();

  await page.goto('/projects/1');
  await expect(page.getByRole('heading', { name: 'Graphene Lab' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Materials');
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).toContainText('Reviews');
  await expect(page.getByRole('navigation', { name: 'Project workflow' })).not.toContainText('Drafts');
  await expect(page.getByRole('region', { name: 'Project summary' })).toContainText('Current tasks');
  await expect(page.getByRole('region', { name: 'Current tasks' })).toContainText('Analyze sample');
  await page.getByRole('region', { name: 'Current tasks' }).getByRole('button', { name: /Analyze sample/ }).click();
  await expect(page.getByRole('region', { name: 'Task details' })).toContainText('Priority: high');
  await expect(page.getByRole('region', { name: 'Pending reviews' })).toContainText(/Review progress_report #\d+/);
  await expect(page.getByRole('region', { name: 'Activity' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toHaveCount(0);
  await page.getByRole('radiogroup', { name: 'Task status' }).getByRole('radio', { name: 'Completed' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Task status updated' }).first()).toBeVisible();
  await expect(page.getByRole('region', { name: 'Current tasks' })).toContainText('completed');

  if (fullStackE2E) {
    await page.getByRole('button', { name: 'Sign out' }).click();
    await loginAs(page, 'student@example.edu');
    await page.goto('/projects/2');
    await expect(page).toHaveURL(/\/login|\/projects\/2/);
    await expect(page.getByText('Quantum Thesis')).not.toBeVisible();
  }
});
