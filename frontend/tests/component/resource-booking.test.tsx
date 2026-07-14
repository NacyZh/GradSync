import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { BookingActions } from '../../src/features/resources/BookingActions';
import { BookingConflictAlert } from '../../src/features/resources/BookingConflictAlert';
import { BookingCalendar } from '../../src/features/resources/BookingCalendar';
import { ResourceListPage } from '../../src/features/resources/ResourceListPage';
import { ResourceUseSubmissionPanel } from '../../src/features/resources/ResourceUseSubmissionPanel';
import { renderWithClient } from './test-utils';

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function futureDateTimeLocal(daysFromNow: number, hour: number) {
  const value = new Date();
  value.setDate(value.getDate() + daysFromNow);
  value.setHours(hour, 0, 0, 0);
  const offsetMs = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offsetMs).toISOString().slice(0, 16);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('resource booking UI', () => {
  it('renders resources shell', () => {
    renderWithClient(<ResourceListPage />);
    expect(screen.getByText('Lab resources')).toBeInTheDocument();
  });

  it('renders conflict message', () => {
    renderWithClient(<BookingConflictAlert message="Unavailable" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Unavailable');
  });

  it('disables cancellation for started bookings', () => {
    renderWithClient(<BookingActions projectId={1} bookingId={1} startsAt="2026-06-25T10:00:00Z" />);

    expect(screen.getByRole('button', { name: 'Cancel booking' })).toBeDisabled();
    expect(screen.getByRole('note')).toHaveTextContent('Started bookings cannot be changed');
  });

  it('shows client feedback when trying to submit a past booking', async () => {
    const { BookingForm } = await import('../../src/features/resources/BookingForm');
    renderWithClient(
      <BookingForm
        projectId={1}
        resources={[{ id: 1, resourceTypeId: 1, name: 'Seat', status: 'available' }]}
        resourceTypes={[{ id: 1, name: 'Seat', scope: 'global', fieldSchema: [], status: 'active' }]}
      />,
    );

    await userEvent.type(screen.getByLabelText('Start'), '2026-06-25T10:00');
    await userEvent.type(screen.getByLabelText('End'), '2026-06-25T11:00');
    await userEvent.click(screen.getByRole('button', { name: 'Reserve' }));

    expect(await screen.findByText(/before the reservation starts/)).toBeInTheDocument();
  });

  it('shows client feedback when booking end is not after start', async () => {
    const { BookingForm } = await import('../../src/features/resources/BookingForm');
    renderWithClient(
      <BookingForm
        projectId={1}
        resources={[{ id: 1, resourceTypeId: 1, name: 'Seat', status: 'available' }]}
        resourceTypes={[{ id: 1, name: 'Seat', scope: 'global', fieldSchema: [], status: 'active' }]}
      />,
    );

    await userEvent.type(screen.getByLabelText('Start'), '2099-06-25T11:00');
    await userEvent.type(screen.getByLabelText('End'), '2099-06-25T10:00');
    await userEvent.click(screen.getByRole('button', { name: 'Reserve' }));

    expect(await screen.findByText(/end time must be after start time/)).toBeInTheDocument();
  });

  it('submits a pending student resource use request with time and quantity', async () => {
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/bookings/') && (!init || init.method === 'GET')) return jsonResponse({ results: [] });
      if (url.endsWith('/api/bookings/') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        return jsonResponse({
          id: 101,
          resourceId: body.resourceId,
          resourceName: 'Confocal microscope',
          requestedById: 7,
          startsAt: body.startsAt,
          endsAt: body.endsAt,
          quantity: body.quantity,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'pending',
          purpose: body.purpose,
          completedAt: null,
          cancelledAt: null,
          createdAt: new Date().toISOString(),
          version: 1,
        }, 201);
      }
      return jsonResponse({ results: [] });
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderWithClient(
      <ResourceUseSubmissionPanel
        canManage={false}
        resources={[{
          id: 41,
          resourceType: 'Microscope',
          resourceTypeId: 7,
          name: 'Confocal microscope',
          status: 'active',
          totalQuantity: 4,
          availableQuantity: 4,
          effectiveConfirmationPolicy: 'approval_required',
          version: 1,
        }]}
      />,
    );

    await userEvent.type(screen.getByLabelText('Start'), futureDateTimeLocal(2, 9));
    await userEvent.type(screen.getByLabelText('End'), futureDateTimeLocal(2, 11));
    await userEvent.clear(screen.getByLabelText('Quantity'));
    await userEvent.type(screen.getByLabelText('Quantity'), '2');
    await userEvent.type(screen.getByLabelText('Purpose'), 'Imaging cells');
    await userEvent.click(screen.getByRole('button', { name: 'Submit use request' }));

    await waitFor(() => {
      const postCall = fetchSpy.mock.calls.find(([url, init]) => String(url).endsWith('/api/bookings/') && init?.method === 'POST');
      expect(postCall).toBeTruthy();
      expect(JSON.parse(String(postCall?.[1]?.body))).toMatchObject({
        resourceId: 41,
        quantity: 2,
        purpose: 'Imaging cells',
      });
    });
    expect(await screen.findByText('Use request pending review')).toBeInTheDocument();
  });

  it('invalidates quantity when selected resource maximum is lower', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ results: [] })));
    renderWithClient(
      <ResourceUseSubmissionPanel
        canManage={false}
        resources={[
          { id: 41, resourceType: 'Microscope', resourceTypeId: 7, name: 'Large scope', status: 'active', totalQuantity: 4, availableQuantity: 4, effectiveConfirmationPolicy: 'approval_required', version: 1 },
          { id: 42, resourceType: 'Microscope', resourceTypeId: 7, name: 'Small scope', status: 'active', totalQuantity: 1, availableQuantity: 1, effectiveConfirmationPolicy: 'approval_required', version: 1 },
        ]}
      />,
    );

    await userEvent.clear(screen.getByLabelText('Quantity'));
    await userEvent.type(screen.getByLabelText('Quantity'), '4');
    await userEvent.click(screen.getByRole('combobox', { name: 'Use resource' }));
    await userEvent.click(screen.getByRole('option', { name: 'Small scope' }));

    await waitFor(() => expect(screen.getByLabelText('Quantity')).toHaveValue(1));
  });

  it('renders cancel action for a not-started student booking', async () => {
    const startsAt = new Date(`${futureDateTimeLocal(3, 9)}:00`).toISOString();
    const endsAt = new Date(`${futureDateTimeLocal(3, 11)}:00`).toISOString();
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/bookings/') && (!init || init.method === 'GET')) {
        return jsonResponse({ results: [{
          id: 101,
          resourceId: 41,
          resourceName: 'Confocal microscope',
          requestedById: 7,
          startsAt,
          endsAt,
          quantity: 2,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'pending',
          version: 1,
        }] });
      }
      if (url.endsWith('/api/bookings/101/cancel/')) {
        return jsonResponse({
          id: 101,
          resourceId: 41,
          resourceName: 'Confocal microscope',
          requestedById: 7,
          startsAt,
          endsAt,
          quantity: 2,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'cancelled',
          cancelledAt: new Date().toISOString(),
          version: 2,
        });
      }
      return jsonResponse({ results: [] });
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderWithClient(
      <ResourceUseSubmissionPanel
        canManage={false}
        resources={[{ id: 41, resourceType: 'Microscope', resourceTypeId: 7, name: 'Confocal microscope', status: 'active', totalQuantity: 4, availableQuantity: 4, effectiveConfirmationPolicy: 'approval_required', version: 1 }]}
      />,
    );

    await userEvent.click(await screen.findByRole('button', { name: 'Cancel request' }));

    await waitFor(() => expect(fetchSpy.mock.calls.some(([url]) => String(url).endsWith('/api/bookings/101/cancel/'))).toBe(true));
    expect(await screen.findByText('Request cancelled')).toBeInTheDocument();
  });

  it('renders advisor review queue rows and approves student requests', async () => {
    const startsAt = new Date(`${futureDateTimeLocal(4, 9)}:00`).toISOString();
    const endsAt = new Date(`${futureDateTimeLocal(4, 11)}:00`).toISOString();
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/bookings/?reviewQueue=true') && (!init || init.method === 'GET')) {
        return jsonResponse({ results: [{
          id: 205,
          resourceId: 41,
          resourceName: 'Confocal microscope',
          requestedById: 7,
          requesterName: 'Student One',
          startsAt,
          endsAt,
          quantity: 1,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'pending',
          purpose: 'Protein imaging',
          version: 1,
        }] });
      }
      if (url.endsWith('/api/bookings/205/approve/')) {
        return jsonResponse({
          id: 205,
          resourceId: 41,
          resourceName: 'Confocal microscope',
          requestedById: 7,
          requesterName: 'Student One',
          startsAt,
          endsAt,
          quantity: 1,
          origin: 'student_request',
          confirmationPolicy: 'approval_required',
          status: 'confirmed',
          purpose: 'Protein imaging',
          version: 2,
        });
      }
      return jsonResponse({ results: [] });
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderWithClient(
      <ResourceUseSubmissionPanel
        canManage
        resources={[{ id: 41, resourceType: 'Microscope', resourceTypeId: 7, name: 'Confocal microscope', status: 'active', totalQuantity: 2, availableQuantity: 2, effectiveConfirmationPolicy: 'approval_required', version: 1 }]}
      />,
    );

    expect(await screen.findByText('Student One · student request')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Approve request' }));

    await waitFor(() => expect(fetchSpy.mock.calls.some(([url]) => String(url).endsWith('/api/bookings/205/approve/'))).toBe(true));
    expect(await screen.findByText('Submission confirmed')).toBeInTheDocument();
  });

  it('records advisor direct use immediately and blocks already-ended periods', async () => {
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/bookings/?reviewQueue=true') && (!init || init.method === 'GET')) return jsonResponse({ results: [] });
      if (url.endsWith('/api/bookings/') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        return jsonResponse({
          id: 301,
          resourceId: body.resourceId,
          resourceName: 'Confocal microscope',
          requestedById: 3,
          requesterName: 'Advisor One',
          startsAt: body.startsAt,
          endsAt: body.endsAt,
          quantity: body.quantity,
          origin: 'staff_direct',
          confirmationPolicy: 'approval_required',
          status: 'confirmed',
          purpose: body.purpose,
          completedAt: null,
          cancelledAt: null,
          createdAt: new Date().toISOString(),
          version: 1,
        }, 201);
      }
      return jsonResponse({ results: [] });
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderWithClient(
      <ResourceUseSubmissionPanel
        canManage
        resources={[{ id: 41, resourceType: 'Microscope', resourceTypeId: 7, name: 'Confocal microscope', status: 'active', totalQuantity: 2, availableQuantity: 2, effectiveConfirmationPolicy: 'approval_required', version: 1 }]}
      />,
    );

    await userEvent.type(screen.getByLabelText('Start'), futureDateTimeLocal(-1, 9));
    await userEvent.type(screen.getByLabelText('End'), futureDateTimeLocal(-1, 11));
    await userEvent.click(screen.getByRole('button', { name: 'Record use' }));

    expect(await screen.findByText('Direct use cannot be recorded after it has ended.')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Start'));
    await userEvent.type(screen.getByLabelText('Start'), futureDateTimeLocal(1, 9));
    await userEvent.clear(screen.getByLabelText('End'));
    await userEvent.type(screen.getByLabelText('End'), futureDateTimeLocal(1, 10));
    await userEvent.type(screen.getByLabelText('Purpose'), 'Calibration');
    await userEvent.click(screen.getByRole('button', { name: 'Record use' }));

    await waitFor(() => {
      const postCall = fetchSpy.mock.calls.find(([url, init]) => String(url).endsWith('/api/bookings/') && init?.method === 'POST');
      expect(postCall).toBeTruthy();
      expect(JSON.parse(String(postCall?.[1]?.body))).toMatchObject({
        resourceId: 41,
        quantity: 1,
        purpose: 'Calibration',
      });
    });
    expect(await screen.findByText('Use recorded')).toBeInTheDocument();
  });

  it('refreshes availability from user events without timer polling', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchSpy = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/resources/availability/')) {
        return jsonResponse({
          observedAt: new Date().toISOString(),
          freshnessToken: String(fetchSpy.mock.calls.length),
          results: [{
            id: 41,
            resourceTypeId: 7,
            resourceType: 'Microscope',
            name: 'Confocal microscope',
            location: 'Room 2',
            status: 'active',
            totalQuantity: 4,
            allocatedQuantity: 1,
            availableQuantity: 3,
            effectiveConfirmationPolicy: 'approval_required',
            version: 1,
            currentUsePeriods: [{
              bookingId: 501,
              startsAt: new Date().toISOString(),
              endsAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
              quantity: 1,
            }],
          }],
        });
      }
      return jsonResponse({ results: [] });
    });
    vi.stubGlobal('fetch', fetchSpy);

    renderWithClient(
      <BookingCalendar
        resource={{
          id: 41,
          resourceType: 'Microscope',
          resourceTypeId: 7,
          name: 'Confocal microscope',
          location: 'Room 2',
          status: 'active',
          totalQuantity: 4,
          availableQuantity: 4,
          effectiveConfirmationPolicy: 'approval_required',
          version: 1,
        }}
        resourceTypes={[{ id: 7, name: 'Microscope', scope: 'global', fieldSchema: [], status: 'active' }]}
      />,
    );

    expect((await screen.findAllByText('Confocal microscope')).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 allocated · 3 available/)).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(5100);
    expect(fetchSpy.mock.calls.filter(([url]) => String(url).includes('/api/resources/availability/'))).toHaveLength(1);

    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(fetchSpy.mock.calls.filter(([url]) => String(url).includes('/api/resources/availability/')).length).toBe(2));
  });
});
