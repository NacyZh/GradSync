import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

function futureDateTimeLocal(daysFromNow: number, hour: number) {
  const value = new Date();
  value.setDate(value.getDate() + daysFromNow);
  value.setHours(hour, 0, 0, 0);
  const offsetMs = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offsetMs).toISOString().slice(0, 16);
}

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) return;

  await page.route('**/api/resource-types/', async (route) => {
    await fulfillJson(route, { results: [{
      id: 7, name: 'Microscope', scope: 'global', fieldSchema: [],
      confirmationPolicy: 'immediate', status: 'active',
    }] });
  });
  await page.route('**/api/resources/', async (route) => {
    await fulfillJson(route, { results: [{
      id: 41, resourceTypeId: 7, resourceType: 'Microscope', name: 'Confocal microscope',
      location: 'Room 2', status: 'active', totalQuantity: 2, availableQuantity: 2,
      effectiveConfirmationPolicy: 'immediate', version: 1,
    }] });
  });
  await page.route('**/api/resources/availability/?**', async (route) => {
    await fulfillJson(route, [
      { id: 41, resourceTypeId: 7, name: 'Confocal microscope', location: 'Room 2', status: 'active', totalQuantity: 2, availableQuantity: 0 },
      { id: 42, resourceTypeId: 7, name: 'Open bench', location: 'Room 3', status: 'active', totalQuantity: 3, availableQuantity: 3 },
    ]);
  });
  await page.route('**/api/resource-use-submissions/', async (route) => {
    await fulfillJson(route, { results: [] });
  });
});

test('resource booking shows availability and handles conflict before success', async ({ page }) => {
  if (fullStackE2E) await loginAs(page, 'student@example.edu');

  let attempts = 0;
  if (!fullStackE2E) {
    await page.route('**/api/bookings/', async (route) => {
      attempts += 1;
      if (attempts === 1) {
        await fulfillJson(route, {
          code: 'insufficient_capacity', availableQuantity: 0, requestedQuantity: 1,
          detail: 'Resource has no remaining capacity for that time window',
        }, 409);
        return;
      }
      await fulfillJson(route, {
        id: 81, resourceId: 41, requestedById: 10,
        startsAt: new Date(`${futureDateTimeLocal(4, 8)}:00`).toISOString(),
        endsAt: new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString(),
        quantity: 1, confirmationPolicy: 'immediate', status: 'confirmed', version: 1,
      }, 201);
    });
  }

  await page.goto('/projects/1/resources');
  await expect(page).toHaveURL(/\/resources$/);
  await expect(page.getByRole('heading', { name: 'Lab resources' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected project context' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Resource list' })).toContainText('Confocal microscope');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Confocal microscope');

  await page.getByLabel('Start', { exact: true }).fill(futureDateTimeLocal(4, 8));
  await page.getByLabel('End', { exact: true }).fill(futureDateTimeLocal(4, 9));
  await page.getByRole('button', { name: 'Reserve' }).click();

  if (fullStackE2E) {
    await expect(page.getByRole('status').filter({ hasText: /Booking (confirmed|submitted)/ }).first()).toBeVisible();
    return;
  }
  await expect(page.getByRole('alert')).toContainText('no remaining capacity');
  await page.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Booking confirmed' }).first()).toBeVisible();
});
