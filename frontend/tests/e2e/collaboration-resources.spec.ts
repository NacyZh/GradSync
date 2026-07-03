import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/resources/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, {
        id: 12,
        name: 'New microscope',
        resourceType: 'Microscope',
        description: 'Shared imaging station',
        status: 'active',
        useInstructions: 'Submit request first.',
        useSubmissions: [],
      }, 201);
      return;
    }
    await fulfillJson(route, {
      results: [{
        id: 7,
        name: 'Confocal microscope',
        resourceType: 'Microscope',
        description: 'Shared imaging station',
        status: 'active',
        useInstructions: 'Submit request first.',
        useSubmissions: [{
          id: 21,
          resourceId: 7,
          studentId: 15,
          studentName: 'Student One',
          submissionType: 'request',
          details: 'Image samples',
          status: 'pending',
        }],
      }],
    });
  });
  await page.route('**/api/resources/7/use-submissions/', async (route) => {
    await fulfillJson(route, {
      id: 22,
      resourceId: 7,
      studentId: 10,
      submissionType: 'request',
      details: 'Use for calibration',
      status: 'pending',
    }, 201);
  });
  await page.route('**/api/resource-use-submissions/21/', async (route) => {
    await fulfillJson(route, {
      id: 21,
      resourceId: 7,
      studentId: 15,
      studentName: 'Student One',
      submissionType: 'request',
      details: 'Image samples',
      status: 'confirmed',
      decisionNote: 'Approved',
    });
  });
});

test('resource inventory and use submissions are role separated', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'advisor@example.edu');
  }

  await page.goto('/projects/1/resources');
  await expect(page.getByRole('heading', { name: 'Lab resources' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resource list' })).toContainText('Confocal microscope');
  await expect(page.getByRole('form', { name: 'Manage resource inventory' })).toBeVisible();
  await expect(page.getByRole('form', { name: 'Submit resource use' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resource use submissions' })).toContainText('Image samples');

  if (!fullStackE2E) {
    await page.getByLabel('Resource name').fill('New microscope');
    await page.getByRole('textbox', { name: 'Resource type' }).fill('Microscope');
    await page.getByRole('button', { name: 'Create resource' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Resource created' }).first()).toBeVisible();

    await page.getByLabel('Use details').fill('Use for calibration');
    await page.getByRole('button', { name: 'Submit use request' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Use submission pending' }).first()).toBeVisible();

    await page.getByRole('button', { name: 'Confirm submission' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Submission confirmed' }).first()).toBeVisible();
  }
});
