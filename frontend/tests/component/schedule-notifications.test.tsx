import { screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';

import { NotificationList } from '../../src/features/notifications/NotificationList';
import { renderWithClient } from './test-utils';

afterEach(() => vi.unstubAllGlobals());

it('renders one schedule reminder with its authorized dashboard deep link', async () => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({
    results: [{
      id: 7,
      event_type: 'schedule_reminder',
      target_type: 'ScheduleItem',
      target_id: '42',
      subject: 'Schedule reminder',
      action_path: '/?date=2026-07-24&item=schedule%3A42',
      status: 'pending',
      eligible_at: '2026-07-24T07:30:00Z',
      deliveryPolicy: 'in_app_email',
    }],
  }), { status: 200, headers: { 'Content-Type': 'application/json' } }))));
  renderWithClient(<NotificationList compact />);
  expect(await screen.findByText('Schedule reminder')).toBeInTheDocument();
  expect(screen.getByText('In-app + email')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Open record' })).toHaveAttribute(
    'href',
    '/?date=2026-07-24&item=schedule%3A42',
  );
});
