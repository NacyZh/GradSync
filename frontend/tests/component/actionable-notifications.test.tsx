import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';

import { NotificationList } from '../../src/features/notifications/NotificationList';
import { NotificationPreferences } from '../../src/features/notifications/NotificationPreferences';
import { I18nProvider } from '../../src/shared/i18n/I18nProvider';
import { renderWithClient } from './test-utils';

afterEach(() => vi.unstubAllGlobals());

it('keeps a read actionable notification pending until it is acknowledged', async () => {
  const requests: Array<{ url: string; method: string }> = [];
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    requests.push({ url, method });
    if (method === 'POST' && url.includes('/acknowledge')) {
      return new Response(JSON.stringify({
        id: 11,
        subject: 'Confirm project scope',
        outcomeState: 'acknowledged',
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify({
      results: [{
        id: 11,
        event_type: 'membership_changed',
        target_type: 'ResearchProject',
        target_id: '7',
        subject: 'Confirm project scope',
        status: 'in_app_only',
        eligible_at: '2026-07-24T08:00:00Z',
        readAt: '2026-07-24T08:01:00Z',
        requirementType: 'acknowledgement',
        outcomeState: 'pending',
        activeFollowUp: true,
        category: 'project',
      }],
      unreadCount: 0,
      pendingActionCount: 1,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }));

  renderWithClient(<NotificationList compact />);
  expect(await screen.findByText('Confirm project scope')).toBeInTheDocument();
  expect(screen.getByText('1 pending actions')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Acknowledge' }));
  expect(requests).toContainEqual(expect.objectContaining({
    url: expect.stringContaining('/api/notifications/11/acknowledge'),
    method: 'POST',
  }));
});

it('renders bilingual preferences with mandatory security and in-app controls fixed', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
    version: 1,
    quietHoursEnabled: false,
    quietHoursStart: null,
    quietHoursEnd: null,
    timezone: 'Asia/Shanghai',
    categories: [{
      category: 'security',
      emailEnabled: true,
      emailRequired: true,
      inAppEnabled: true,
    }],
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })));

  renderWithClient(
    <I18nProvider locale="zh">
      <NotificationPreferences />
    </I18nProvider>,
  );

  expect(await screen.findByText('通知偏好')).toBeInTheDocument();
  expect(screen.getByText('站内通知始终启用。')).toBeInTheDocument();
  const checkboxes = screen.getAllByRole('checkbox');
  expect(checkboxes[1]).toBeChecked();
  expect(checkboxes[1]).toBeDisabled();
});
