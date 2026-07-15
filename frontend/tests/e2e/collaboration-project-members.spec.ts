import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/projects/1/', async (route) => {
    await fulfillJson(route, {
      id: 1,
      title: 'Graphene Lab',
      description: 'Research operations validation',
      status: 'active',
      memberships: [
        { id: 1, projectId: 1, userId: 10, nickname: 'Advisor One', email: 'advisor@example.edu', role: 'advisor', status: 'active' },
        { id: 2, projectId: 1, userId: 12, nickname: 'Student One', email: 'student.one@example.edu', role: 'student', status: 'active' },
      ],
      current_tasks: [],
      pending_reviews: [],
      upcoming_bookings: [],
      activity: [],
    });
  });
  await page.route('**/api/accounts/students/?**', async (route) => {
    await fulfillJson(route, [
      { id: 13, nickname: 'Alex', email: 'alex.one@example.edu', degreeType: 'masters', label: 'Alex <alex.one@example.edu>' },
      { id: 14, nickname: 'Alex', email: 'alex.two@example.edu', degreeType: 'doctoral', label: 'Alex <alex.two@example.edu>' },
    ]);
  });
  await page.route('**/api/projects/1/members/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, {
        id: 4,
        projectId: 1,
        userId: 14,
        nickname: 'Alex',
        email: 'alex.two@example.edu',
        role: 'student',
        status: 'active',
      }, 201);
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/projects/1/members/2/', async (route) => {
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/projects/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, {
        id: 9,
        title: 'Selected Student Project',
        description: '',
        status: 'active',
        memberships: [
          { id: 8, projectId: 9, userId: 14, nickname: 'Alex', email: 'alex.two@example.edu', role: 'student', status: 'active' },
        ],
      }, 201);
      return;
    }
    await fulfillJson(route, { capabilities: { canCreateProject: true }, results: [] });
  });
});

test('teacher manages project membership by student nickname', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'advisor@example.edu');
  }

  await page.goto('/projects/1');
  await expect(page.getByRole('heading', { name: 'Graphene Lab' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Project members' })).toContainText(
    fullStackE2E ? 'student@example.edu' : 'student.one@example.edu',
  );

  if (!fullStackE2E) {
    await page.getByLabel('Student nickname').fill('Alex');
    await expect(page.getByText('alex.one@example.edu')).toBeVisible();
    await expect(page.getByText('doctoral')).toBeVisible();
    await page.getByText('alex.two@example.edu').click();
    await expect(page.getByText('Member added')).toBeVisible();

    await page.getByRole('button', { name: 'Remove Student One' }).click();
    await expect(page.getByRole('dialog', { name: 'Remove student?' })).toBeVisible();
    await page.getByRole('dialog', { name: 'Remove student?' }).getByRole('button', { name: 'Remove student' }).click();
    await expect(page.getByText('Member removed')).toBeVisible();
  }
});

test('teacher creates a project with selected student accounts', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'advisor@example.edu');
  }

  await page.goto('/projects/new');
  await page.getByLabel('Project title').fill('Selected Student Project');

  if (!fullStackE2E) {
    await page.getByLabel('Student nickname').fill('Alex');
    await expect(page.getByText('alex.one@example.edu')).toBeVisible();
    await page.getByText('alex.two@example.edu').click();
    await expect(page.getByRole('list', { name: 'Selected students' })).toContainText('Alex <alex.two@example.edu>');
  }

  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('Created project Selected Student Project')).toBeVisible();
});
