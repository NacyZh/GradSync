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
