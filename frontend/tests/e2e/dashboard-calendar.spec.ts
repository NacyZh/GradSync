import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) await loginAs(page);
});

for (const viewport of [
  { width: 390, height: 900 },
  { width: 900, height: 950 },
  { width: 1440, height: 950 },
]) {
  test(`dashboard calendar remains usable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');

    await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
    await expect(page.getByRole('group', { name: 'Calendar view' })).toBeVisible();
    await page.getByRole('button', { name: 'Agenda' }).click();
    await expect(page.getByRole('button', { name: 'Agenda' })).toHaveAttribute('aria-pressed', 'true');

    const regionBox = await page.getByRole('region', { name: 'Dashboard calendar' }).boundingBox();
    expect(regionBox).not.toBeNull();
    expect((regionBox?.x ?? 0) + (regionBox?.width ?? 0)).toBeLessThanOrEqual(viewport.width + 1);
  });
}

test('calendar source item opens a read-only detail before navigation', async ({ page }) => {
  await page.goto('/');
  if (fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
    return;
  }

  await page.getByRole('button', { name: /Analyze sample/ }).first().click();
  await expect(page.getByRole('complementary', { name: 'Schedule details' })).toContainText('Read-only project data');
  await expect(page.getByRole('link', { name: 'Open source' })).toHaveAttribute('href', '/projects/1?task=11');
  await expect(page.getByRole('button', { name: /Edit/ })).toHaveCount(0);
});

test('advisor dashboard includes configured project report deadline', async ({ page }) => {
  await page.goto('/');
  if (fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
    return;
  }

  await expect(page.getByRole('grid').getByRole('button', { name: /Graphene Lab: weekly report due/ })).toBeVisible();
  await page.getByRole('button', { name: /Filter calendar sources/ }).click();
  await expect(page.getByRole('group', { name: 'Calendar sources' }).getByText('Reports')).toBeVisible();
});

test('notification query context selects the authorized occurrence', async ({ page }) => {
  await page.goto('/?date=2026-07-24&item=task%3A11%3A2026-07-24T08%3A00%3A00Z');
  await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
  if (!fullStackE2E) {
    await expect(page.getByRole('complementary', { name: 'Schedule details' })).toContainText('Analyze sample');
  }
});

test('calendar workspace is available to admin advisor and student roles', async ({ page }) => {
  if (fullStackE2E) {
    await page.goto('/');
    await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
    return;
  }

  const cases = [
    { role: 'advisor', heading: 'Advisor workspace' },
    { role: 'student', heading: 'Student workspace' },
    { role: 'admin', heading: 'Operations workspace' },
  ] as const;
  for (const item of cases) {
    await page.unroute('**/api/accounts/me/');
    await page.route('**/api/accounts/me/', async (route) => {
      await route.fulfill({
        json: {
          id: 40,
          email: `${item.role}@example.edu`,
          name: item.role,
          global_role: item.role,
          status: 'active',
        },
      });
    });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: item.heading })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Dashboard calendar' })).toBeVisible();
  }
});

test('authenticated user creates an owner-only schedule from the dashboard', async ({ page }) => {
  await page.goto('/');
  const createRequest = page.waitForRequest((request) => request.url().includes('/api/schedules/') && request.method() === 'POST');
  await page.getByRole('button', { name: 'New schedule' }).click();
  await page.getByLabel('Title').fill('Private literature review');
  await page.getByRole('button', { name: 'Create schedule' }).click();

  const request = await createRequest;
  expect(request.postDataJSON()).toMatchObject({ scope: 'personal', title: 'Private literature review' });
  await expect(page.getByText('Schedule created', { exact: true })).toBeVisible();
});
