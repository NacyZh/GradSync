import { useMutation } from '@tanstack/react-query';

import { cancelBooking } from './api';

export function BookingActions({ projectId, bookingId }: { projectId?: number; bookingId?: number }) {
  const mutation = useMutation({ mutationFn: () => cancelBooking(projectId ?? 0, bookingId ?? 0) });

  return (
    <>
      <button type="button" onClick={() => mutation.mutate()}>
        Cancel booking
      </button>
      {mutation.isSuccess ? <span role="status">Booking cancelled</span> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </>
  );
}
