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
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/resources/', async (route) => {
    await fulfillJson(route, { results: [{ id: 41, name: 'Confocal microscope', resource_type: 'equipment', location: 'Room 2', status: 'available' }] });
  });
  await page.route('**/api/resources/availability/?**', async (route) => {
    await fulfillJson(route, [
      { id: 41, name: 'Confocal microscope', resource_type: 'equipment', location: 'Room 2', status: 'available', available: false, conflicting_booking_count: 1 },
      { id: 42, name: 'Open bench', resource_type: 'seat', location: 'Room 3', status: 'available', available: true, conflicting_booking_count: 0 },
    ]);
  });
  await page.route('**/api/projects/1/bookings/', async (route) => {
    if (route.request().method() === 'GET') {
      await fulfillJson(route, {
        results: [{
          id: 81,
          project_id: 1,
          resource_id: 41,
          starts_at: new Date(`${futureDateTimeLocal(4, 8)}:00`).toISOString(),
          ends_at: new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString(),
          status: 'reserved',
        }],
      });
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/projects/1/bookings/81/cancel/', async (route) => {
    await fulfillJson(route, {
      id: 81,
      project_id: 1,
      resource_id: 41,
      starts_at: new Date(`${futureDateTimeLocal(4, 8)}:00`).toISOString(),
      ends_at: new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString(),
      status: 'cancelled',
    });
  });
});

test('resource booking shows availability and handles conflict before success', async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'student@example.edu');
  }
  let attempts = 0;
  if (!fullStackE2E) {
    await page.route('**/api/projects/1/bookings/', async (route) => {
      if (route.request().method() === 'GET') {
        await fulfillJson(route, {
          results: [{
            id: 81,
            project_id: 1,
            resource_id: 41,
            starts_at: new Date(`${futureDateTimeLocal(4, 8)}:00`).toISOString(),
            ends_at: new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString(),
            status: 'reserved',
          }],
        });
        return;
      }
      attempts += 1;
      if (attempts === 1) {
        await fulfillJson(route, { message: 'Resource is already reserved for that time window' }, 400);
        return;
      }
      await fulfillJson(route, {
        id: 81,
        project_id: 1,
        resource_id: 41,
        starts_at: new Date(`${futureDateTimeLocal(4, 8)}:00`).toISOString(),
        ends_at: new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString(),
        status: 'reserved',
      }, 201);
    });
  }

  await page.goto('/projects/1/resources');
  await expect(page.getByRole('heading', { name: 'Lab resources' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected project context' })).toContainText('Graphene Lab');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Confocal microscope');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Open bench');

  if (fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Available');
    await page.getByLabel('Start', { exact: true }).fill(futureDateTimeLocal(4, 8));
    await page.getByLabel('End', { exact: true }).fill(futureDateTimeLocal(4, 9));
    await page.getByRole('button', { name: 'Reserve' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Booking confirmed' }).first()).toBeVisible();
    await page.getByRole('button', { name: 'Cancel booking' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Cancel booking?' })).toBeVisible();
    await page.getByRole('dialog', { name: 'Cancel booking?' }).getByRole('button', { name: 'Cancel booking' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Booking cancelled' }).first()).toBeVisible();
    return;
  }

  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Unavailable · 1 conflict');
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Available');
  await page.getByLabel('Start', { exact: true }).fill(futureDateTimeLocal(4, 8));
  await page.getByLabel('End', { exact: true }).fill(futureDateTimeLocal(4, 9));
  await page.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByRole('alert')).toContainText('Resource is already reserved');
  await page.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Booking confirmed' }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Cancel booking' }).click();
  await expect(page.getByRole('dialog', { name: 'Cancel booking?' })).toBeVisible();
  await page.getByRole('dialog', { name: 'Cancel booking?' }).getByRole('button', { name: 'Cancel booking' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Booking cancelled' }).first()).toBeVisible();
});
