import { useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';
import { LockKeyhole, Trash2 } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { cancelBooking } from './api';

export function BookingActions({
  projectId,
  bookingId,
  startsAt,
  compact = false,
}: {
  projectId?: number;
  bookingId?: number;
  startsAt?: string;
  compact?: boolean;
}) {
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
    <div className={compact ? 'grid justify-items-start gap-2' : 'grid gap-2'}>
      <Button variant="destructive" size={compact ? 'sm' : 'default'} type="button" onClick={onCancel} disabled={hasStarted || mutation.isPending}>
        <Trash2 className="h-4 w-4" aria-hidden="true" />
        Cancel booking
      </Button>
      {hasStarted ? (
        <span role="note" className="inline-flex items-start gap-2 text-xs font-bold text-muted-foreground">
          <LockKeyhole className="mt-0.5 h-3.5 w-3.5 text-warning" aria-hidden="true" />
          Started bookings cannot be changed.
        </span>
      ) : null}
      {mutation.isSuccess ? <DataState state="success" message="Booking cancelled" className="py-2" /> : null}
      {mutation.error ? <span role="alert">{mutation.error.message}</span> : null}
    </div>
  );
}
