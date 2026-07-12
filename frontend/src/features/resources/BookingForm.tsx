import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CalendarPlus } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/primitives/select';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { KeyboardHint, useAppFeedback, useSubmitShortcut } from '../../shared/ui/AppFeedback';
import { DataState } from '../../shared/ui/DataState';
import { FormStatus } from '../../shared/ui/FormStatus';
import type { ResourceItem, ResourceType } from './api';
import { createBooking } from './api';

type BookingFormProps = {
  resources?: ResourceItem[];
  resourceTypes?: ResourceType[];
  defaultStartsAt?: string;
  defaultEndsAt?: string;
  disabled?: boolean;
};

export function BookingForm({ resources = [], resourceTypes = [], defaultStartsAt = '', defaultEndsAt = '', disabled = false }: BookingFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const { notify } = useAppFeedback();
  const availableResources = useMemo(
    () => resources.filter((resource) => resource.status !== 'retired' && resource.status !== 'unavailable'),
    [resources],
  );
  const [selectedResourceId, setSelectedResourceId] = useState('');
  const resourceTypeById = useMemo(() => new Map(resourceTypes.map((type) => [type.id, type])), [resourceTypes]);
  useEffect(() => {
    if (availableResources.length === 0) {
      setSelectedResourceId('');
      return;
    }
    if (!availableResources.some((resource) => String(resource.id) === selectedResourceId)) {
      setSelectedResourceId(String(availableResources[0].id));
    }
  }, [availableResources, selectedResourceId]);
  const mutation = useMutation({
    mutationFn: (payload: { resourceId: number; startsAt: string; endsAt: string; quantity: number; purpose?: string }) => createBooking(payload),
    onSuccess: (booking) => notify(booking.status === 'pending' ? 'Booking submitted for approval' : 'Booking confirmed', 'success'),
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
      resourceId: Number(form.get('resourceId')),
      startsAt,
      endsAt,
      quantity: Number(form.get('quantity')),
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
        <p className="text-sm text-muted-foreground">Reserve shared inventory for a future time window.</p>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="bookingQuantity">Quantity</Label>
        <Input id="bookingQuantity" name="quantity" type="number" min="1" defaultValue="1" required disabled={disabled} />
      </div>
      {disabled ? <DataState state="warning" title="Select a valid window" message="Resolve the availability window before submitting a booking." /> : null}
      {availableResources.length === 0 ? (
        <DataState state="filtered-empty" title="No bookable resources" message="No available resources match the current filters." />
      ) : null}
      <div className="grid gap-1.5">
        <Label htmlFor="bookingResource">Resource</Label>
        <Select name="resourceId" required value={selectedResourceId} onValueChange={setSelectedResourceId} disabled={disabled || availableResources.length === 0}>
          <SelectTrigger id="bookingResource" aria-label="Resource">
            <SelectValue placeholder="Choose a resource" />
          </SelectTrigger>
          <SelectContent>
            {availableResources.map((resource) => (
              <SelectItem key={resource.id} value={String(resource.id)}>
                {resource.name} · {resourceTypeById.get(resource.resourceTypeId)?.name ?? 'Resource'}
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
        <Textarea id="bookingPurpose" name="purpose" placeholder="Experiment, meeting, or research need" disabled={disabled} />
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
