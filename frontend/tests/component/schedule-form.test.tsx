import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ScheduleFormDialog } from '../../src/features/schedules/ScheduleFormDialog';
import { ScheduleDetailPanel } from '../../src/features/schedules/ScheduleDetailPanel';
import { renderWithClient } from './test-utils';

describe('schedule form', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('creates a private schedule with recurrence and reminders', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithClient(
      <ScheduleFormDialog open onOpenChange={() => undefined} role="student" onSubmit={onSubmit} />,
    );

    expect(screen.queryByLabelText('Visibility')).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Title'), 'Private planning block');
    await userEvent.selectOptions(screen.getByLabelText('Repeats'), 'weekly');
    await userEvent.type(screen.getByLabelText('Repeat until'), '2026-08-31');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Monday' }));
    await userEvent.click(screen.getByRole('button', { name: 'Create schedule' }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      scope: 'personal',
      title: 'Private planning block',
      recurrence: expect.objectContaining({ frequency: 'weekly', weekdays: [1] }),
    }));
  });

  it('keeps staff audience candidates inside searchable dropdowns', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({
      results: [{ id: 1, type: 'project', label: 'Graphene Lab', secondaryLabel: 'Active research project', status: 'active', eligible: true, eligibilityScope: 'manageable_project_member' }],
      nextCursor: null,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))));
    renderWithClient(
      <ScheduleFormDialog open onOpenChange={() => undefined} role="advisor" onSubmit={vi.fn()} />,
    );

    await userEvent.click(screen.getByLabelText('Visibility'));
    await userEvent.click(screen.getByRole('option', { name: 'Group' }));
    expect(screen.queryByText('Graphene Lab')).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Projects'));
    expect(await screen.findByRole('option', { name: /Graphene Lab/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('option', { name: /Graphene Lab/ }));
    expect(screen.getByRole('list', { name: 'Selected projects' })).toHaveTextContent('Graphene Lab');
    expect(screen.queryByText(/all accounts/i)).not.toBeInTheDocument();
  });

  it('confirms group cancellation without exposing delete', async () => {
    const onCancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.includes('delivery-status')
        ? { scheduleId: 9, resolvedRecipients: { active: 2, removed: 0 }, notifications: { inAppCreated: 2, inAppClaimed: 0, emailSent: 0, emailQueued: 0, emailFailed: 0, skipped: 0 }, deliveryPolicy: { publication: 'in_app', ordinaryChange: 'in_app', cancellation: 'in_app_email', reminder: 'in_app_email' }, failureCodes: [], updatedAt: '2026-07-20T08:00:00Z' }
        : { results: [] };
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }));
    renderWithClient(<ScheduleDetailPanel
      occurrence={{
        occurrenceId: 'schedule:9:2026-07-21T09:00:00+00:00',
        sourceType: 'schedule',
        sourceId: '9',
        scheduleId: 9,
        scope: 'group',
        category: 'meeting',
        title: 'Research sync',
        allDay: false,
        startsAt: '2026-07-21T09:00:00Z',
        endsAt: '2026-07-21T10:00:00Z',
        timezone: 'UTC',
        status: 'active',
        version: 3,
        capabilities: { canView: true, canEdit: true, canDelete: false, canPublish: false, canCancel: true, canViewDeliveryStatus: true, isReadOnly: false },
      }}
      onCancel={onCancel}
    />);
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel schedule' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm cancellation' }));
    expect(onCancel).toHaveBeenCalledWith('series', '2026-07-21T09:00:00+00:00');
  });
});
