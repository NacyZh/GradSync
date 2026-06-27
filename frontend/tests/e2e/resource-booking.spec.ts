import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.route('**/api/resources/', async (route) => {
    await fulfillJson(route, { results: [{ id: 41, name: 'Confocal microscope', resource_type: 'equipment', location: 'Room 2', status: 'available' }] });
  });
  await page.route('**/api/resources/availability/?**', async (route) => {
    await fulfillJson(route, [
      { id: 41, name: 'Confocal microscope', resource_type: 'equipment', location: 'Room 2', status: 'available', available: false, conflicting_booking_count: 1 },
      { id: 42, name: 'Open bench', resource_type: 'seat', location: 'Room 3', status: 'available', available: true, conflicting_booking_count: 0 },
    ]);
  });
});

test('resource booking shows availability and handles conflict before success', async ({ page }) => {
  let attempts = 0;
  await page.route('**/api/projects/1/bookings/', async (route) => {
    attempts += 1;
    if (attempts === 1) {
      await fulfillJson(route, { message: 'Resource is already reserved for that time window' }, 400);
      return;
    }
    await fulfillJson(route, { id: 81, project_id: 1, resource_id: 41, starts_at: '2026-06-27T08:00:00Z', ends_at: '2026-06-27T09:00:00Z', status: 'reserved' }, 201);
  });

  await page.goto('/projects/1/resources');
  await expect(page.getByRole('heading', { name: 'Lab resources' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Confocal microscope: Unavailable');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Open bench: Available');
  await page.getByLabel('Start', { exact: true }).fill('2026-06-27T08:00');
  await page.getByLabel('End', { exact: true }).fill('2026-06-27T09:00');
  await page.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByRole('alert')).toContainText('Resource is already reserved');
  await page.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByText('Booking confirmed')).toBeVisible();
});
