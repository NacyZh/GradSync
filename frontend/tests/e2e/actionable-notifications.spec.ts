import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, mockAuthenticatedApi } from './api-mocks';

test('actionable notification drawer separates unread from pending action', async ({ page }) => {
  test.skip(fullStackE2E, 'Authoritative lifecycle is covered by backend integration.');
  await page.setViewportSize({ width: 390, height: 844 });
  await mockAuthenticatedApi(page);
  let read = false;
  let acknowledged = false;
  await page.route('**/api/notifications', async (route) => {
    await fulfillJson(route, {
      results: [{
        id: 91,
        event_type: 'membership_changed',
        target_type: 'ResearchProject',
        target_id: '1',
        subject: 'Confirm project scope',
        action_path: '/projects/1',
        status: 'in_app_only',
        eligible_at: '2026-07-24T08:00:00Z',
        readAt: read ? '2026-07-24T08:01:00Z' : null,
        requirementType: 'acknowledgement',
        outcomeState: acknowledged ? 'acknowledged' : 'pending',
        activeFollowUp: !acknowledged,
      }],
      unreadCount: read ? 0 : 1,
      pendingActionCount: acknowledged ? 0 : 1,
    });
  });
  await page.route('**/api/notifications/read', async (route) => {
    read = true;
    await fulfillJson(route, { readAt: '2026-07-24T08:01:00Z', updatedIds: [91] });
  });
  await page.route('**/api/notifications/91/acknowledge', async (route) => {
    acknowledged = true;
    await fulfillJson(route, { id: 91, outcomeState: 'acknowledged' });
  });

  await page.goto('/');
  await expect(page.getByTestId('notification-unread-dot')).toBeVisible();
  await page.getByRole('button', { name: 'Open notifications' }).click();
  await expect(page.getByText('1 pending actions')).toBeVisible();
  for (const width of [390, 900, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const drawer = await page.getByRole('dialog', { name: 'Notifications' }).boundingBox();
    expect(drawer).not.toBeNull();
    expect(drawer!.width).toBeLessThanOrEqual(width);
    expect(drawer!.width).toBeGreaterThanOrEqual(width < 768 ? width - 1 : width / 2 - 1);
  }
  await page.getByRole('button', { name: 'Acknowledge' }).click();
  await expect(page.getByText('Notification acknowledged')).toBeVisible();
});
