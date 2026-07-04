import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { NotificationList } from '../../src/features/notifications/NotificationList';
import { renderWithClient } from './test-utils';

describe('collaboration notification status UI', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows retry-needed, pending, sent, skipped, and failure detail states', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(
        JSON.stringify({
          results: [
            {
              id: 1,
              project_id: 7,
              recipient_email: 'student@example.edu',
              event_type: 'teacher_feedback_available',
              target_type: 'TeacherFeedback',
              target_id: '9',
              subject: 'Feedback available',
              action_path: '/projects/7/writing',
              status: 'retry_needed',
              eligible_at: '2026-07-03T09:00:00Z',
              last_attempt_at: '2026-07-03T08:55:00Z',
              retry_count: 2,
              failure_reason: 'SMTP provider unavailable',
            },
            {
              id: 2,
              eventType: 'verification_code',
              relatedObjectType: 'EmailVerificationCode',
              relatedObjectId: '12',
              subject: 'Verify your GradSync email',
              actionPath: '/verify-email',
              status: 'sent',
              eligibleAt: '2026-07-03T08:00:00Z',
              sentAt: '2026-07-03T08:01:00Z',
            },
            {
              id: 3,
              event_type: 'resource_use_decision',
              target_type: 'ResourceUseSubmission',
              target_id: '21',
              subject: 'Resource use confirmed',
              action_path: '/resources',
              status: 'skipped',
              eligible_at: '2026-07-03T08:30:00Z',
              failure_reason: 'Recipient is no longer active',
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )),
    );

    renderWithClient(<NotificationList />);

    expect(await screen.findByText('Feedback available')).toBeInTheDocument();
    expect(screen.getByText('1 needs retry')).toBeInTheDocument();
    expect(screen.getByText('1 skipped')).toBeInTheDocument();
    expect(screen.getByText('teacher feedback available')).toBeInTheDocument();
    expect(screen.getByText('SMTP provider unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry needed (2)' })).toBeDisabled();
    expect(screen.getByText('Verify your GradSync email')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();
    expect(screen.getByText('Resource use confirmed')).toBeInTheDocument();
    expect(screen.getByText('Skipped')).toBeInTheDocument();
  });
});
