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
      {
        id: 41,
        resourceTypeId: 7,
        name: 'Confocal microscope',
        location: 'Room 2',
        status: 'active',
        totalQuantity: 2,
        availableQuantity: 0,
        allocatedQuantity: 2,
        currentUsePeriods: [{
          bookingId: 501,
          startsAt: '2099-01-01T09:00:00Z',
          endsAt: '2099-01-01T10:00:00Z',
          quantity: 2,
        }],
      },
      { id: 42, resourceTypeId: 7, name: 'Open bench', location: 'Room 3', status: 'active', totalQuantity: 3, availableQuantity: 3 },
    ]);
  });
  await page.route('**/api/bookings/?resourceId=**', async (route) => {
    await fulfillJson(route, { results: [{
      id: 501,
      resourceId: 41,
      resourceName: 'Confocal microscope',
      requestedById: 10,
      startsAt: '2099-01-01T09:00:00Z',
      endsAt: '2099-01-01T10:00:00Z',
      quantity: 2,
      origin: 'staff_direct',
      confirmationPolicy: 'immediate',
      status: 'confirmed',
      version: 1,
    }] });
  });
});

test('resource booking shows availability and handles conflict before success', async ({ page }) => {
  if (fullStackE2E) await loginAs(page, 'student@example.edu');

  let attempts = 0;
  if (!fullStackE2E) {
    await page.route('**/api/bookings/', async (route) => {
      if (route.request().method() !== 'POST') {
        await fulfillJson(route, { results: [] });
        return;
      }
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
  if (!fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Selected resource availability' })).toContainText('Use periods');
    await expect(page.getByRole('region', { name: 'Selected resource availability' })).toContainText('Qty 2');
  }
  await expect(page.getByRole('region', { name: 'Booking calendar' })).toContainText('Confocal microscope');

  const reserveForm = page.getByRole('form', { name: 'Reserve resource' });
  await reserveForm.getByLabel('Start').fill(futureDateTimeLocal(4, 8));
  await reserveForm.getByLabel('End').fill(futureDateTimeLocal(4, 9));
  await reserveForm.getByRole('button', { name: 'Reserve' }).click();

  if (fullStackE2E) {
    await expect(page.getByRole('status').filter({ hasText: /Booking (confirmed|submitted)/ }).first()).toBeVisible();
    return;
  }
  await expect(page.getByRole('status').filter({ hasText: 'Resource has no remaining capacity' }).first()).toBeVisible();
  await reserveForm.getByRole('button', { name: 'Reserve' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Booking confirmed' }).first()).toBeVisible();
});

test('student submits and cancels a resource use request', async ({ page }) => {
  if (fullStackE2E) await loginAs(page, 'student@example.edu');

  if (!fullStackE2E) {
    await page.unroute('**/api/accounts/me/').catch(() => undefined);
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, {
        id: 10,
        email: 'student@example.edu',
        name: 'Student One',
        global_role: 'student',
        status: 'active',
      });
    });
    const bookings: Array<Record<string, unknown>> = [];
    await page.route('**/api/bookings/', async (route) => {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON();
        const created = {
          id: 91,
          resourceId: body.resourceId,
          resourceName: 'Confocal microscope',
          requestedById: 10,
          startsAt: body.startsAt,
          endsAt: body.endsAt,
          quantity: body.quantity,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'pending',
          purpose: body.purpose,
          completedAt: null,
          cancelledAt: null,
          createdAt: new Date().toISOString(),
          version: 1,
        };
        bookings.splice(0, bookings.length, created);
        await fulfillJson(route, created, 201);
        return;
      }
      await fulfillJson(route, { results: bookings });
    });
    await page.route('**/api/bookings/91/cancel/', async (route) => {
      const cancelled = { ...bookings[0], status: 'cancelled', cancelledAt: new Date().toISOString(), version: 2 };
      bookings.splice(0, bookings.length, cancelled);
      await fulfillJson(route, cancelled);
    });
  }

  await page.goto('/resources');
  const useForm = page.getByRole('form', { name: 'Submit resource use' });
  await useForm.getByLabel('Start').fill(futureDateTimeLocal(5, 9));
  await useForm.getByLabel('End').fill(futureDateTimeLocal(5, 11));
  await useForm.getByLabel('Quantity').fill('2');
  await useForm.getByLabel('Purpose').fill('Imaging cells');
  await useForm.getByRole('button', { name: 'Submit use request' }).click();

  await expect(page.getByRole('status').filter({ hasText: 'Use request pending review' }).first()).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resource use submissions' })).toContainText('pending');

  await page
    .getByRole('region', { name: 'Resource use submissions' })
    .getByRole('button', { name: 'Cancel request' })
    .first()
    .click();
  await expect(page.getByRole('status').filter({ hasText: 'Request cancelled' }).first()).toBeVisible();
});

test('advisor approves and rejects student resource use requests', async ({ page }) => {
  test.skip(fullStackE2E, 'mocked review queue scenario exercises the UI contract deterministically');

  await page.unroute('**/api/accounts/me/').catch(() => undefined);
  await page.route('**/api/accounts/me/', async (route) => {
    await fulfillJson(route, {
      id: 20,
      email: 'advisor@example.edu',
      name: 'Advisor One',
      global_role: 'advisor',
      status: 'active',
    });
  });

  const startsAt = new Date(`${futureDateTimeLocal(6, 9)}:00`).toISOString();
  const endsAt = new Date(`${futureDateTimeLocal(6, 11)}:00`).toISOString();
  const queue = [
    {
      id: 501,
      resourceId: 41,
      resourceName: 'Confocal microscope',
      requestedById: 10,
      requesterName: 'Student One',
      startsAt,
      endsAt,
      quantity: 1,
      origin: 'student_request',
      confirmationPolicy: 'approval_required',
      status: 'pending',
      purpose: 'Imaging cells',
      version: 1,
    },
    {
      id: 502,
      resourceId: 41,
      resourceName: 'Confocal microscope',
      requestedById: 11,
      requesterName: 'Student Two',
      startsAt,
      endsAt,
      quantity: 1,
      origin: 'student_request',
      confirmationPolicy: 'approval_required',
      status: 'pending',
      purpose: 'Training',
      version: 1,
    },
  ];

  await page.route('**/api/bookings/?reviewQueue=true', async (route) => {
    await fulfillJson(route, { results: queue });
  });
  await page.route('**/api/bookings/501/approve/', async (route) => {
    queue.splice(0, 1);
    await fulfillJson(route, { id: 501, status: 'confirmed' });
  });
  await page.route('**/api/bookings/502/reject/', async (route) => {
    queue.splice(0, 1);
    await fulfillJson(route, { id: 502, status: 'rejected' });
  });

  await page.goto('/resources');
  const submissions = page.getByRole('region', { name: 'Resource use submissions' });
  await expect(submissions).toContainText('Student One');
  await expect(submissions).toContainText('Student Two');

  await submissions.getByRole('button', { name: 'Approve request' }).first().click();
  await expect(page.getByRole('status').filter({ hasText: 'Submission confirmed' }).first()).toBeVisible();

  await submissions.getByRole('button', { name: 'Reject request' }).first().click();
  await expect(submissions).toContainText('0 pending');
});

test('advisor records direct resource use without review', async ({ page }) => {
  test.skip(fullStackE2E, 'mocked direct-use scenario exercises the UI contract deterministically');

  await page.unroute('**/api/accounts/me/').catch(() => undefined);
  await page.route('**/api/accounts/me/', async (route) => {
    await fulfillJson(route, {
      id: 20,
      email: 'advisor@example.edu',
      name: 'Advisor One',
      global_role: 'admin',
      status: 'active',
    });
  });
  await page.route('**/api/bookings/?reviewQueue=true', async (route) => {
    await fulfillJson(route, { results: [] });
  });
  await page.route('**/api/bookings/', async (route) => {
    if (route.request().method() !== 'POST') {
      await fulfillJson(route, { results: [] });
      return;
    }
    const body = route.request().postDataJSON();
    await fulfillJson(route, {
      id: 601,
      resourceId: body.resourceId,
      resourceName: 'Confocal microscope',
      requestedById: 20,
      requesterName: 'Advisor One',
      startsAt: body.startsAt,
      endsAt: body.endsAt,
      quantity: body.quantity,
      origin: 'staff_direct',
      confirmationPolicy: 'approval_required',
      status: 'confirmed',
      purpose: body.purpose,
      version: 1,
    }, 201);
  });

  await page.goto('/resources');
  const useForm = page.getByRole('form', { name: 'Submit resource use' });
  await expect(useForm).toContainText('Record your own current or future use without approval.');
  await useForm.getByLabel('Start').fill(futureDateTimeLocal(7, 9));
  await useForm.getByLabel('End').fill(futureDateTimeLocal(7, 10));
  await useForm.getByLabel('Quantity').fill('1');
  await useForm.getByLabel('Purpose').fill('Calibration');
  await useForm.getByRole('button', { name: 'Record use' }).click();

  await expect(page.getByRole('status').filter({ hasText: 'Use recorded' }).first()).toBeVisible();
});
