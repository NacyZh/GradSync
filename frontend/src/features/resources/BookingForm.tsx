import { useMutation } from '@tanstack/react-query';

import { FormStatus } from '../../shared/ui/FormStatus';
import type { LabResource } from './api';
import { createBooking } from './api';

export function BookingForm({ projectId, resources = [] }: { projectId?: number; resources?: LabResource[] }) {
  const mutation = useMutation({ mutationFn: (payload: { resource_id: number; starts_at: string; ends_at: string }) => createBooking(projectId ?? 0, payload) });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      resource_id: Number(form.get('resourceId')),
      starts_at: String(form.get('startsAt')),
      ends_at: String(form.get('endsAt')),
    });
  }

  return (
    <form aria-label="Reserve resource" onSubmit={onSubmit}>
      <label>
        Resource
        <select name="resourceId" required>
          {resources.map((resource) => (
            <option key={resource.id} value={resource.id}>
              {resource.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Start
        <input name="startsAt" type="datetime-local" />
      </label>
      <label>
        End
        <input name="endsAt" type="datetime-local" />
      </label>
      <button type="submit">Reserve</button>
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Booking confirmed' : undefined} />
    </form>
  );
}
