import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../src/features/auth/AuthProvider';
import { ResourceListPage } from '../../src/features/resources/ResourceListPage';
import { renderWithClient } from './test-utils';

type MockResult = { body?: unknown; status?: number } | unknown;

function mockFetch(handler: (url: string, init?: RequestInit) => MockResult) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const result = handler(String(input), init);
    const wrapped = result && typeof result === 'object' && (
      'body' in result || (typeof (result as { status?: unknown }).status === 'number')
    )
      ? result as { body?: unknown; status?: number }
      : { body: result, status: 200 };
    return new Response(wrapped.status === 204 ? null : JSON.stringify(wrapped.body), {
      status: wrapped.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;
}

function resource(overrides: Record<string, unknown> = {}) {
  return {
    id: 2,
    name: 'Confocal microscope',
    resourceTypeId: 1,
    resourceType: 'Microscope',
    totalQuantity: 3,
    availableQuantity: 3,
    status: 'active',
    confirmationPolicyOverride: null,
    effectiveConfirmationPolicy: 'immediate',
    version: 1,
    ...overrides,
  };
}

function renderResources() {
  return renderWithClient(<AuthProvider><MemoryRouter initialEntries={['/resources']}><Routes><Route path="/resources" element={<ResourceListPage />} /></Routes></MemoryRouter></AuthProvider>);
}

describe('collaboration resources UI', () => {
  it('creates and edits quantity-aware inventory with saved values', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    mockFetch((url, init) => {
      requests.push({ url, init });
      if (url.includes('/api/accounts/me/')) return { id: 10, global_role: 'advisor', status: 'active' };
      if (url.endsWith('/api/resources/') && init?.method === 'POST') return resource({ id: 3, name: 'New microscope' });
      if (url.includes('/api/resources/2/') && init?.method === 'PATCH') return resource({ name: 'Updated microscope', totalQuantity: 4, version: 2 });
      if (url.endsWith('/api/resources/')) return { results: [resource()] };
      if (url.includes('/resource-items/availability/')) return [];
      if (url.includes('/resource-types')) return { results: [] };
      return { results: [] };
    });
    renderResources();

    expect((await screen.findAllByText('Confocal microscope')).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('button', { name: 'Create resource' }));
    await userEvent.type(screen.getByLabelText('Resource name'), 'New microscope');
    await userEvent.type(screen.getByLabelText('Resource type'), 'Microscope');
    await userEvent.clear(screen.getByLabelText('Total quantity'));
    await userEvent.type(screen.getByLabelText('Total quantity'), '2');
    await userEvent.click(within(screen.getByRole('form', { name: 'Create resource' })).getByRole('button', { name: 'Create resource' }));
    await waitFor(() => expect(requests.some(({ init }) => init?.method === 'POST')).toBe(true));

    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    expect(screen.getByLabelText('Resource name')).toHaveValue('Confocal microscope');
    expect(screen.getByLabelText('Total quantity')).toHaveValue(3);
  });

  it('confirms permanent deletion and offers retirement after a dependency conflict', async () => {
    let deleteAttempts = 0;
    mockFetch((url, init) => {
      if (url.includes('/api/accounts/me/')) return { id: 10, global_role: 'admin', status: 'active' };
      if (url.includes('/api/resources/2/') && init?.method === 'DELETE') {
        deleteAttempts += 1;
        return { status: 409, body: { code: 'resource_has_history', canRetire: true, detail: 'Resource has history' } };
      }
      if (url.includes('/api/resources/2/retire/') && init?.method === 'POST') return resource({ status: 'retired', version: 2 });
      if (url.endsWith('/api/resources/')) return { results: [resource()] };
      if (url.includes('/resource-items/availability/')) return [];
      if (url.includes('/resource-types')) return { results: [] };
      return { results: [] };
    });
    renderResources();

    await screen.findAllByText('Confocal microscope');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(screen.getByText(/immutable deletion audit snapshot/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Delete resource' }));
    await waitFor(() => expect(deleteAttempts).toBe(1));
    expect(await screen.findByRole('button', { name: 'Retire resource' })).toBeInTheDocument();
  });

  it('hides inventory mutations from students', async () => {
    mockFetch((url) => {
      if (url.includes('/api/accounts/me/')) return { id: 11, global_role: 'student', status: 'active' };
      if (url.endsWith('/api/resources/')) return { results: [resource()] };
      if (url.includes('/resource-items/availability/')) return [];
      if (url.includes('/resource-types')) return { results: [] };
      return { results: [] };
    });
    renderResources();
    await screen.findAllByText('Confocal microscope');
    expect(screen.queryByRole('button', { name: 'Create resource' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
  });

  it('keeps the resource workspace regions in the required reading order', async () => {
    mockFetch((url) => {
      if (url.includes('/api/accounts/me/')) return { id: 11, global_role: 'student', status: 'active' };
      if (url.endsWith('/api/resources/')) return { results: [resource()] };
      if (url.includes('/api/resources/availability/')) return { observedAt: new Date().toISOString(), freshnessToken: '1', results: [resource()] };
      if (url.includes('/resource-types')) return { results: [] };
      return { results: [] };
    });
    renderResources();

    await screen.findAllByText('Confocal microscope');
    const resourceList = screen.getByRole('region', { name: 'Resource list' });
    const availability = screen.getByRole('region', { name: 'Booking calendar' });
    const useForm = screen.getByRole('form', { name: 'Submit resource use' });
    const submissions = screen.getByRole('region', { name: 'Resource use submissions' });

    expect(resourceList.compareDocumentPosition(availability) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(availability.compareDocumentPosition(useForm) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(useForm.compareDocumentPosition(submissions) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('renders booking review queue without reading legacy use-submission records', async () => {
    mockFetch((url) => {
      if (url.includes('/api/accounts/me/')) return { id: 10, global_role: 'advisor', status: 'active' };
      if (url.endsWith('/api/resources/')) return { results: [resource()] };
      if (url.includes('/api/bookings/?reviewQueue=true')) {
        return { results: [{
          id: 9,
          resourceId: 2,
          resourceName: 'Confocal microscope',
          requestedById: 11,
          requesterName: 'Student One',
          startsAt: '2099-01-01T09:00:00Z',
          endsAt: '2099-01-01T10:00:00Z',
          quantity: 1,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'pending',
          purpose: 'Booking queue row',
          version: 1,
        }] };
      }
      if (url.includes('/resource-types')) return { results: [] };
      return { results: [] };
    });

    renderResources();

    expect((await screen.findAllByText('Confocal microscope')).length).toBeGreaterThan(0);
    expect(await screen.findByText('Booking queue row')).toBeInTheDocument();
    expect(screen.queryByText('Use records unavailable')).not.toBeInTheDocument();
  });
});
