import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AccountAdminPage } from '../../src/features/admin/AccountAdminPage';
import { NotificationList } from '../../src/features/notifications/NotificationList';
import { renderWithClient } from './test-utils';

describe('notification and account administration UI', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders delivery status, project context, action path, and failure reason', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(
        JSON.stringify({
          results: [
            {
              id: 1,
              project_id: 7,
              event_type: 'pending_review',
              target_type: 'progress_report',
              target_id: '12',
              subject: 'Report review pending',
              action_path: '/projects/7/reviews',
              status: 'failed',
              eligible_at: '2026-06-25T10:00:00Z',
              failure_reason: 'SMTP provider rejected the recipient',
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )),
    );

    renderWithClient(<NotificationList projectId={7} />);

    expect(await screen.findByText('Report review pending')).toBeInTheDocument();
    expect(screen.getByText('pending review')).toBeInTheDocument();
    expect(screen.getByText('Project #7')).toBeInTheDocument();
    expect(screen.getByText('progress report #12')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('SMTP provider rejected the recipient');
    expect(screen.getByRole('link', { name: 'Open record' })).toHaveAttribute('href', '/projects/7/reviews');
    expect(screen.getByRole('button', { name: 'Retry queued by worker' })).toBeDisabled();
  });

  it('filters account records and exposes dense role-safe controls', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(
        JSON.stringify({
          count: 3,
          next: null,
          previous: null,
          results: [
            { id: 1, email: 'admin@test.local', name: 'Admin', global_role: 'admin', status: 'active' },
            { id: 2, email: 'advisor@test.local', name: 'Advisor', global_role: 'advisor', status: 'suspended' },
            { id: 3, email: 'student@test.local', name: 'Student', global_role: 'student', status: 'archived' },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )),
    );

    renderWithClient(<AccountAdminPage />);

    expect(await screen.findByRole('heading', { name: 'Account administration' })).toBeInTheDocument();
    expect(await screen.findByText('admin@test.local')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('combobox', { name: 'Account status filter' }));
    await userEvent.click(screen.getByRole('option', { name: 'Suspended' }));

    expect(screen.getByText('advisor@test.local')).toBeInTheDocument();
    expect(screen.queryByText('admin@test.local')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reactivate' })).toBeInTheDocument();
  });

  it('does not expose account creation and confirms destructive archive actions', async () => {
    const calls: RequestInit[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, init = {}) => {
        calls.push(init);
        if (init.method === 'POST' && String(init.body).includes('archive')) {
          return new Response(JSON.stringify({ id: 1, email: 'admin@test.local', name: 'Admin', global_role: 'admin', status: 'archived' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(
          JSON.stringify({
            count: 1,
            next: null,
            previous: null,
            results: [{ id: 1, email: 'admin@test.local', name: 'Admin', global_role: 'admin', status: 'active' }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderWithClient(<AccountAdminPage />);

    await screen.findByText('admin@test.local');
    expect(screen.queryByRole('button', { name: 'Create account' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Archive' }));
    const dialog = await screen.findByRole('dialog', { name: 'Archive account?' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Archive account' }));

    await waitFor(() => expect(calls.some((call) => String(call.body).includes('archive'))).toBe(true));
  });
});
