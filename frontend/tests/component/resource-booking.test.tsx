import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { BookingActions } from '../../src/features/resources/BookingActions';
import { BookingConflictAlert } from '../../src/features/resources/BookingConflictAlert';
import { ResourceListPage } from '../../src/features/resources/ResourceListPage';
import { renderWithClient } from './test-utils';

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
      <BookingForm projectId={1} resources={[{ id: 1, name: 'Seat', resource_type: 'seat', status: 'available' }]} />,
    );

    await userEvent.type(screen.getByLabelText('Start'), '2026-06-25T10:00');
    await userEvent.type(screen.getByLabelText('End'), '2026-06-25T11:00');
    await userEvent.click(screen.getByRole('button', { name: 'Reserve' }));

    expect(await screen.findByText(/before the reservation starts/)).toBeInTheDocument();
  });

  it('shows client feedback when booking end is not after start', async () => {
    const { BookingForm } = await import('../../src/features/resources/BookingForm');
    renderWithClient(
      <BookingForm projectId={1} resources={[{ id: 1, name: 'Seat', resource_type: 'seat', status: 'available' }]} />,
    );

    await userEvent.type(screen.getByLabelText('Start'), '2099-06-25T11:00');
    await userEvent.type(screen.getByLabelText('End'), '2099-06-25T10:00');
    await userEvent.click(screen.getByRole('button', { name: 'Reserve' }));

    expect(await screen.findByText(/end time must be after start time/)).toBeInTheDocument();
  });
});
