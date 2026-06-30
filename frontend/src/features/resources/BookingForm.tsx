import { useMutation } from '@tanstack/react-query';
import { useCallback, useMemo, useRef } from 'react';

import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { FormStatus } from '../../shared/ui/FormStatus';
import type { LabResource } from './api';
import { createBooking } from './api';

export function BookingForm({ projectId, resources = [] }: { projectId?: number; resources?: LabResource[] }) {
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const availableResources = useMemo(() => resources.filter((resource) => resource.status !== 'retired'), [resources]);
  const mutation = useMutation({
    mutationFn: (payload: { resource_id: number; starts_at: string; ends_at: string; purpose?: string }) => createBooking(projectId ?? 0, payload),
    onSuccess: () => notify('Booking confirmed', 'success'),
    onError: (error) => notify(error.message, 'error'),
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const startsAt = String(form.get('startsAt'));
    const endsAt = String(form.get('endsAt'));
    const startsAtMs = new Date(startsAt).getTime();
    const endsAtMs = new Date(endsAt).getTime();
    if (startsAtMs <= Date.now()) {
      notify('Bookings can only be changed before the reservation starts', 'error');
      return;
    }
    if (endsAtMs <= startsAtMs) {
      notify('Booking end time must be after start time', 'error');
      return;
    }
    mutation.mutate({
      resource_id: Number(form.get('resourceId')),
      starts_at: startsAt,
      ends_at: endsAt,
      purpose: String(form.get('purpose') ?? ''),
    });
  }

  const submitShortcut = useCallback(() => {
    formRef.current?.requestSubmit();
  }, []);
  useSubmitShortcut(submitShortcut);

  return (
    <form ref={formRef} className="stacked-form panel" aria-label="Reserve resource" onSubmit={onSubmit}>
      <h2>Reserve resource</h2>
      <label>
        Resource
        <select name="resourceId" required>
          {availableResources.map((resource) => (
            <option key={resource.id} value={resource.id}>
              {resource.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Start
        <input name="startsAt" type="datetime-local" required />
      </label>
      <label>
        End
        <input name="endsAt" type="datetime-local" required />
      </label>
      <label>
        Purpose
        <textarea name="purpose" placeholder="Project work, experiment, or meeting need" />
      </label>
      <button type="submit">Reserve</button>
      <KeyboardHint>Ctrl+Enter reserves</KeyboardHint>
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Booking confirmed' : undefined} />
    </form>
  );
}
