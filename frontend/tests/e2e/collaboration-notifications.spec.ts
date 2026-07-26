import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('notification degradation flow exposes retry status', async ({ page }) => {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    await loginAs(page);
    await page.goto('/projects/1');
    await page.getByRole('button', { name: 'Open notifications' }).click();
    await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText(
      'Pending review reminder',
    );
    await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText(
      '1 pending',
    );
    return;
  }

  await page.route('**/api/notifications', async (route) => {
    await fulfillJson(route, {
      results: [
        {
          id: 31,
          project_id: 1,
          event_type: 'teacher_feedback_available',
          target_type: 'TeacherFeedback',
          target_id: '17',
          subject: 'Feedback available',
          action_path: '/projects/1/writing',
          status: 'retry_needed',
          eligible_at: '2026-07-03T09:05:00Z',
          last_attempt_at: '2026-07-03T09:00:00Z',
          retry_count: 1,
          failure_reason: 'SMTP provider unavailable',
        },
        {
          id: 32,
          project_id: 1,
          event_type: 'resource_use_decision',
          target_type: 'ResourceUseSubmission',
          target_id: '9',
          subject: 'Resource use confirmed',
          action_path: '/projects/1/resources',
          status: 'sent',
          eligible_at: '2026-07-03T08:00:00Z',
          sent_at: '2026-07-03T08:01:00Z',
        },
      ],
    });
  });

  await page.goto('/projects/1');
  await page.getByRole('button', { name: 'Open notifications' }).click();

  await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText('Feedback available');
  await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText('1 needs retry');
  await expect(page.getByRole('alert')).toContainText('SMTP provider unavailable');
  await expect(page.getByRole('button', { name: 'Retry needed (1)' })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Open record' }).first()).toHaveAttribute('href', '/projects/1/writing');
});

test('schedule reminder uses one top notification and dashboard deep link', async ({ page }) => {
  test.skip(fullStackE2E, 'schedule reminder generation is covered by backend integration');
  await mockAuthenticatedApi(page);
  await page.route('**/api/notifications', async (route) => {
    await fulfillJson(route, {
      results: [{
        id: 44,
        event_type: 'schedule_reminder',
        target_type: 'ScheduleItem',
        target_id: '9',
        subject: 'Schedule reminder',
        action_path: '/?date=2026-07-24&item=schedule%3A9%3A2026-07-24T08%3A00%3A00Z',
        status: 'pending',
        deliveryPolicy: 'in_app_email',
        eligible_at: '2026-07-24T07:30:00Z',
      }],
    });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open notifications' }).click();
  const center = page.getByRole('region', { name: 'Notifications', exact: true });
  await expect(center.getByRole('listitem')).toHaveCount(1);
  await expect(center.getByRole('listitem')).toContainText('Schedule reminder');
  await expect(center).toContainText('In-app + email');
  await expect(center.getByRole('link', { name: 'Open record' })).toHaveAttribute(
    'href',
    '/?date=2026-07-24&item=schedule%3A9%3A2026-07-24T08%3A00%3A00Z',
  );
});

test('notification drawer clears viewed state and restores the red dot for new records', async ({ page }) => {
  test.skip(fullStackE2E, 'Read receipt persistence is covered by the backend contract journey.');
  await mockAuthenticatedApi(page);
  let notifications = [{
    id: 51,
    event_type: 'pending_review',
    target_type: 'WeeklyProgressReport',
    target_id: '12',
    subject: 'Review requested',
    action_path: '/projects/1/reviews',
    status: 'pending',
    eligible_at: '2026-07-20T08:00:00Z',
    readAt: null as string | null,
  }];
  await page.route('**/api/notifications', async (route) => {
    await fulfillJson(route, { results: notifications });
  });

  await page.setViewportSize({ width: 1440, height: 950 });
  await page.goto('/');
  await expect(page.getByTestId('notification-unread-dot')).toBeVisible();
  const readRequest = page.waitForRequest((request) => (
    request.url().endsWith('/api/notifications/read') && request.method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Open notifications' }).click();
  expect((await readRequest).postDataJSON()).toEqual({ notificationIds: [51] });
  await expect(page.getByTestId('notification-unread-dot')).toHaveCount(0);

  const drawer = page.getByRole('dialog', { name: 'Notifications' });
  await expect(drawer).toBeVisible();
  const drawerBox = await drawer.boundingBox();
  expect(drawerBox?.width).toBeGreaterThanOrEqual(700);
  expect(drawerBox?.width).toBeLessThanOrEqual(721);
  await page.getByRole('button', { name: 'Close' }).click();

  notifications = [
    {
      ...notifications[0],
      readAt: '2026-07-20T08:01:00Z',
    },
    {
      ...notifications[0],
      id: 52,
      subject: 'New review requested',
      readAt: null,
    },
  ];
  await page.reload();
  await expect(page.getByTestId('notification-unread-dot')).toBeVisible();
});
