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
      }],
    });
  });
  await page.route('**/api/bookings**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/api/bookings/21/approve/')) {
      await fulfillJson(route, { id: 21, status: 'confirmed' });
      return;
    }
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await fulfillJson(route, {
        id: 22,
        resourceId: body.resourceId,
        resourceName: 'Confocal microscope',
        requestedById: 10,
        startsAt: body.startsAt,
        endsAt: body.endsAt,
        quantity: body.quantity,
        origin: 'staff_direct',
        confirmationPolicy: 'approval_required',
        status: 'confirmed',
        purpose: body.purpose,
        version: 1,
      }, 201);
      return;
    }
    if (url.searchParams.get('reviewQueue') === 'true') {
      await fulfillJson(route, { results: [{
        id: 21,
        resourceId: 7,
        resourceName: 'Confocal microscope',
        requestedById: 15,
        requesterName: 'Student One',
        startsAt: '2099-01-01T09:00:00Z',
        endsAt: '2099-01-01T10:00:00Z',
        quantity: 1,
        origin: 'student_request',
        confirmationPolicy: 'approval_required',
        status: 'pending',
        purpose: 'Image samples',
        version: 1,
      }] });
      return;
    }
    await fulfillJson(route, { results: [] });
  });
});

test('resource inventory and use submissions are role separated', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'advisor@example.edu');
  }

  await page.goto('/projects/1/resources');
  await expect(page.getByRole('heading', { name: 'Lab resources' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resource list' })).toContainText('Confocal microscope');
  const useForm = page.getByRole('form', { name: 'Submit resource use' });
  await expect(useForm).toBeVisible();
  if (fullStackE2E) {
    await expect(useForm.getByLabel('Use resource')).toBeVisible();
    await expect(useForm.getByLabel('Purpose')).toBeVisible();
    await expect(useForm.getByRole('button', { name: 'Record use' })).toBeVisible();
    return;
  }

  await expect(page.getByRole('region', { name: 'Resource use submissions' })).toContainText('Image samples');

  await page.getByRole('button', { name: 'Create resource' }).click();
  await expect(page.getByRole('dialog', { name: 'Create resource' })).toBeVisible();
  await page.getByLabel('Resource name').fill('New microscope');
  await page.getByRole('textbox', { name: 'Resource type' }).fill('Microscope');
  await page.getByRole('button', { name: 'Create resource' }).click();
  await expect(page.getByRole('dialog', { name: 'Create resource' })).toHaveCount(0);

  await useForm.getByLabel('Start').fill('2099-01-02T09:00');
  await useForm.getByLabel('End').fill('2099-01-02T10:00');
  await useForm.getByLabel('Purpose').fill('Use for calibration');
  await useForm.getByRole('button', { name: 'Record use' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Use recorded' }).first()).toBeVisible();

  await page.getByRole('button', { name: 'Approve request' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Submission confirmed' }).first()).toBeVisible();
});
