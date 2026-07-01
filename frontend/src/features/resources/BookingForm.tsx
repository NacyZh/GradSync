import { useMutation } from '@tanstack/react-query';
import { useCallback, useMemo, useRef } from 'react';
import { CalendarPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import type { LabResource } from './api';
import { createBooking } from './api';

type BookingFormProps = {
  projectId?: number;
  resources?: LabResource[];
  defaultStartsAt?: string;
  defaultEndsAt?: string;
  disabled?: boolean;
};

export function BookingForm({ projectId, resources = [], defaultStartsAt = '', defaultEndsAt = '', disabled = false }: BookingFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const availableResources = useMemo(
    () => resources.filter((resource) => resource.status !== 'retired' && resource.status !== 'unavailable'),
    [resources],
  );
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
    if (!Number(form.get('resourceId'))) {
      notify('Choose an available resource before reserving', 'error');
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
    <form ref={formRef} className="panel grid gap-4" aria-label="Reserve resource" onSubmit={onSubmit}>
      <div>
        <h2 className="flex items-center gap-2">
          <CalendarPlus className="h-4 w-4" aria-hidden="true" />
          Reserve resource
        </h2>
        <p className="text-sm text-muted-foreground">Create a project-scoped booking with a future time window.</p>
      </div>
      {disabled ? <DataState state="warning" title="Select a valid window" message="Resolve the availability window before submitting a booking." /> : null}
      {availableResources.length === 0 ? (
        <DataState state="filtered-empty" title="No bookable resources" message="No available resources match the current filters." />
      ) : null}
      <div className="grid gap-1.5">
        <Label htmlFor="bookingResource">Resource</Label>
        <Select name="resourceId" required defaultValue={availableResources[0] ? String(availableResources[0].id) : undefined} disabled={disabled || availableResources.length === 0}>
          <SelectTrigger id="bookingResource" aria-label="Resource">
            <SelectValue placeholder="Choose a resource" />
          </SelectTrigger>
          <SelectContent>
            {availableResources.map((resource) => (
              <SelectItem key={resource.id} value={String(resource.id)}>
                {resource.name} · {resource.resource_type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label htmlFor="bookingStartsAt">Start</Label>
          <Input id="bookingStartsAt" name="startsAt" type="datetime-local" defaultValue={defaultStartsAt} required disabled={disabled} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="bookingEndsAt">End</Label>
          <Input id="bookingEndsAt" name="endsAt" type="datetime-local" defaultValue={defaultEndsAt} required disabled={disabled} />
        </div>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="bookingPurpose">Purpose</Label>
        <Textarea id="bookingPurpose" name="purpose" placeholder="Project work, experiment, or meeting need" disabled={disabled} />
      </div>
      <Button type="submit" disabled={disabled || mutation.isPending || availableResources.length === 0}>
        <CalendarPlus className="h-4 w-4" aria-hidden="true" />
        Reserve
      </Button>
      <KeyboardHint>Ctrl+Enter reserves</KeyboardHint>
      <FormStatus error={mutation.error?.message} success={mutation.isSuccess ? 'Booking confirmed' : undefined} />
    </form>
  );
}
