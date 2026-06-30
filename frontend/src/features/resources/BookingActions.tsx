import { useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { cancelBooking } from './api';

export function BookingActions({ projectId, bookingId, startsAt }: { projectId?: number; bookingId?: number; startsAt?: string }) {
  const { confirm, notify } = useAppFeedback();
  const hasStarted = useMemo(
    () => (startsAt ? new Date(startsAt).getTime() <= Date.now() : false),
    [startsAt],
  );
  const mutation = useMutation({
    mutationFn: () => cancelBooking(projectId ?? 0, bookingId ?? 0),
    onSuccess: () => notify('Booking cancelled', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  async function onCancel() {
    if (hasStarted) {
      notify('Bookings can only be changed before the reservation starts', 'error');
      return;
    }
    const ok = await confirm({
      title: 'Cancel booking?',
      message: 'This will release the reservation and notify affected project members.',
      actionLabel: 'Cancel booking',
    });
    if (ok) mutation.mutate();
  }

  return (
    <>
      <button className="button danger" type="button" onClick={onCancel} disabled={hasStarted}>
        Cancel booking
      </button>
      {hasStarted ? <span role="note">Started bookings cannot be changed.</span> : null}
      {mutation.isSuccess ? <span role="status">Booking cancelled</span> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </>
  );
}
