import { expect, test } from '@playwright/test';

import { buildCalendarOccurrence, buildCalendarResponse, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) await loginAs(page);
});

test('advisor publishes to selected project from dropdown without broadcast control', async ({ page }) => {
  await page.goto('/');
  if (fullStackE2E) {
    await expect(page.getByRole('button', { name: 'New schedule' })).toBeVisible();
    return;
  }
  await page.getByRole('button', { name: 'New schedule' }).click();
  await page.getByLabel('Visibility').click();
  await page.getByRole('option', { name: 'Group' }).click();
  await page.getByLabel('Title').fill('Methods review meeting');
  await page.getByLabel('Projects').click();
  await page.getByRole('option', { name: /Graphene Lab/ }).click();
  await expect(page.getByRole('list', { name: 'Selected projects' })).toContainText('Graphene Lab');
  await expect(page.getByText(/all accounts/i)).toHaveCount(0);

  const requestPromise = page.waitForRequest((request) => request.url().endsWith('/api/schedules/') && request.method() === 'POST');
  await page.getByRole('button', { name: 'Publish schedule' }).click();
  await page.getByRole('dialog', { name: 'Publish group schedule' }).getByRole('button', { name: 'Publish schedule' }).click();
  const request = await requestPromise;
  expect(request.postDataJSON()).toMatchObject({ scope: 'group', audience: { projectIds: [1] } });
  await expect(page.getByText('Schedule published', { exact: true })).toBeVisible();
});

test('student schedule form has no group publication controls', async ({ page }) => {
  if (fullStackE2E) {
    await page.goto('/');
    return;
  }
  await page.unroute('**/api/accounts/me/');
  await page.route('**/api/accounts/me/', (route) => route.fulfill({ json: { id: 12, email: 'student@example.edu', name: 'Student', global_role: 'student', status: 'active' } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'New schedule' }).click();
  await expect(page.getByLabel('Visibility')).toHaveCount(0);
  await expect(page.getByText('Audience', { exact: true })).toHaveCount(0);
});

test('publisher confirms group cancellation and sees delivery totals', async ({ page }) => {
  test.skip(fullStackE2E, 'covered by backend contract in full-stack mode');
  const groupItem = buildCalendarOccurrence({
    occurrenceId: 'schedule:9:2026-07-24T08:00:00Z',
    sourceType: 'schedule',
    sourceId: '9',
    scheduleId: 9,
    scope: 'group',
    category: 'meeting',
    title: 'Research sync',
    status: 'active',
    version: 2,
    capabilities: { canView: true, canEdit: true, canDelete: false, canPublish: false, canCancel: true, canViewDeliveryStatus: true, isReadOnly: false },
  });
  await page.route('**/api/calendar/occurrences/**', (route) => route.fulfill({ json: buildCalendarResponse([groupItem]) }));
  await page.route('**/api/schedules/9/revisions/**', (route) => route.fulfill({ json: { count: 0, results: [] } }));
  await page.route('**/api/schedules/9/delivery-status/**', (route) => route.fulfill({ json: {
    scheduleId: 9,
    resolvedRecipients: { active: 3, removed: 1 },
    notifications: { inAppCreated: 3, inAppClaimed: 0, emailSent: 0, emailQueued: 0, emailFailed: 0, skipped: 0 },
    deliveryPolicy: { publication: 'in_app', ordinaryChange: 'in_app', cancellation: 'in_app_email', reminder: 'in_app_email' },
    failureCodes: [],
    updatedAt: '2026-07-20T08:00:00Z',
  } }));
  await page.route('**/api/schedules/9/cancel/**', (route) => route.fulfill({ json: { ...groupItem, status: 'cancelled', version: 3 } }));
  await page.goto('/');
  await page.getByRole('button', { name: /Research sync.*schedule/ }).click();
  await expect(page.getByLabel('Delivery status')).toContainText('Active recipients');
  await page.getByRole('button', { name: 'Cancel schedule' }).click();
  const requestPromise = page.waitForRequest((request) => request.url().includes('/api/schedules/9/cancel/'));
  await page.getByRole('button', { name: 'Confirm cancellation' }).click();
  expect((await requestPromise).postDataJSON()).toMatchObject({ changeScope: 'series', confirmed: true });
  await expect(page.getByText('Schedule cancelled', { exact: true })).toBeVisible();
});
