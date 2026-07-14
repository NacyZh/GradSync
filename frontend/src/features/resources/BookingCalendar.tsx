import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarClock, Filter, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { BookingConflictAlert } from './BookingConflictAlert';
import { BookingForm } from './BookingForm';
import type { Booking, LaboratoryResource, ResourceItem, ResourceType } from './api';
import { cancelBooking, listBookings, listResourceAvailability, returnBooking } from './api';

function toDateTimeLocal(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

type BookingCalendarProps = {
  resource?: LaboratoryResource;
  resourceTypes?: ResourceType[];
  onWindowChange?: (window: { startsAt: string; endsAt: string; hasValidWindow: boolean }) => void;
  onAvailabilityChange?: (availability: ResourceItem[]) => void;
};

export function BookingCalendar({ resource, resourceTypes = [], onWindowChange, onAvailabilityChange }: BookingCalendarProps) {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => {
    const start = new Date();
    start.setDate(start.getDate() + 1);
    start.setMinutes(0, 0, 0);
    const end = new Date(start);
    end.setHours(end.getHours() + 2);
    return { startsAt: toDateTimeLocal(start), endsAt: toDateTimeLocal(end) };
  }, []);
  const [startsAt, setStartsAt] = useState(defaults.startsAt);
  const [endsAt, setEndsAt] = useState(defaults.endsAt);
  const startsAtMs = new Date(startsAt).getTime();
  const endsAtMs = new Date(endsAt).getTime();
  const hasValidWindow = Number.isFinite(startsAtMs) && Number.isFinite(endsAtMs) && startsAtMs > Date.now() && endsAtMs > startsAtMs;
  const invalidWindowMessage = startsAtMs <= Date.now()
    ? 'Availability searches must use a future start time.'
    : endsAtMs <= startsAtMs
      ? 'Availability end must be after the start time.'
      : '';
  const availabilityQuery = useQuery({
    queryKey: ['resource-availability', startsAt, endsAt],
    queryFn: () => listResourceAvailability(startsAt, endsAt),
    enabled: hasValidWindow,
    refetchOnWindowFocus: true,
    placeholderData: (previous) => previous,
  });
  const usePeriodsQuery = useQuery({
    queryKey: ['bookings', 'resource-periods', resource?.id],
    queryFn: () => listBookings({ resourceId: resource?.id }),
    enabled: Boolean(resource?.id),
    refetchOnWindowFocus: true,
    placeholderData: (previous) => previous,
  });
  const availability = useMemo(() => availabilityQuery.data?.results ?? [], [availabilityQuery.data]);
  const usePeriodBookings = useMemo(() => (usePeriodsQuery.data?.results ?? [])
    .filter((booking) => booking.resourceId === resource?.id && !['completed', 'cancelled', 'rejected'].includes(booking.status))
    .sort((first, second) => new Date(first.startsAt).getTime() - new Date(second.startsAt).getTime()), [resource?.id, usePeriodsQuery.data]);
  const selectedAvailability = availability.find((item) => item.id === resource?.id);
  const bookingResource = selectedAvailability ?? (resource ? {
    ...resource,
    status: resource.status === 'active' ? 'available' : resource.status,
  } : undefined);
  const availableQuantity = bookingResource ? bookingResource.availableQuantity ?? bookingResource.totalQuantity : 0;
  const isUnavailable = Boolean(bookingResource && availableQuantity < 1);
  const observedAt = availabilityQuery.data?.observedAt;
  function refreshResourceState() {
    void queryClient.invalidateQueries({ queryKey: ['bookings'] });
    void queryClient.invalidateQueries({ queryKey: ['resources'] });
    void queryClient.invalidateQueries({ queryKey: ['resource-availability'] });
  }
  const returnMutation = useMutation({
    mutationFn: returnBooking,
    onSuccess: refreshResourceState,
  });
  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: refreshResourceState,
  });

  const updateWindow = useCallback((nextStartsAt = startsAt, nextEndsAt = endsAt) => {
    const nextStartsAtMs = new Date(nextStartsAt).getTime();
    const nextEndsAtMs = new Date(nextEndsAt).getTime();
    onWindowChange?.({
      startsAt: nextStartsAt,
      endsAt: nextEndsAt,
      hasValidWindow: Number.isFinite(nextStartsAtMs) && Number.isFinite(nextEndsAtMs) && nextStartsAtMs > Date.now() && nextEndsAtMs > nextStartsAtMs,
    });
  }, [endsAt, onWindowChange, startsAt]);

  useEffect(() => {
    updateWindow();
  }, [updateWindow]);

  useEffect(() => {
    onAvailabilityChange?.(availability);
  }, [availability, onAvailabilityChange]);

  return (
    <section className="panel" aria-label="Booking calendar">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4" aria-hidden="true" />
            Availability
          </h2>
          <p className="text-sm text-muted-foreground">Choose a future window before reserving or checking conflicts.</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Badge variant="secondary">
            <Filter className="h-3.5 w-3.5" aria-hidden="true" />
            {resource ? resource.name : 'No resource selected'}
          </Badge>
          <Button type="button" variant="outline" size="sm" onClick={() => availabilityQuery.refetch()} disabled={!hasValidWindow || availabilityQuery.isFetching}>
            <RefreshCw className={`h-4 w-4 ${availabilityQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label htmlFor="availabilityStartsAt">Availability start</Label>
          <Input
            id="availabilityStartsAt"
            name="availabilityStartsAt"
            type="datetime-local"
            value={startsAt}
            onChange={(event) => {
              setStartsAt(event.target.value);
              updateWindow(event.target.value, endsAt);
            }}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="availabilityEndsAt">Availability end</Label>
          <Input
            id="availabilityEndsAt"
            name="availabilityEndsAt"
            type="datetime-local"
            value={endsAt}
            onChange={(event) => {
              setEndsAt(event.target.value);
              updateWindow(startsAt, event.target.value);
            }}
          />
        </div>
      </div>
      {!hasValidWindow && invalidWindowMessage ? (
        <BookingConflictAlert title="Invalid availability window" message={invalidWindowMessage} />
      ) : null}
      {availabilityQuery.isLoading ? <DataState state="loading" message="Checking resource availability." className="mt-4" /> : null}
      {observedAt ? <p className="mt-3 text-xs text-muted-foreground" role="status">Availability observed {new Date(observedAt).toLocaleTimeString()}</p> : null}
      {availabilityQuery.isFetching && !availabilityQuery.isLoading ? <p className="mt-3 text-xs text-muted-foreground" role="status">Updating availability…</p> : null}
      {availabilityQuery.error ? <DataState state="error" title="Availability unavailable" message={`${availabilityQuery.error.message}${availability.length ? ' Showing last known availability.' : ''}`} className="mt-4" /> : null}
      {isUnavailable ? (
        <BookingConflictAlert
          title="Conflict in this window"
          message={`${resource?.name ?? 'This resource'} has no remaining capacity. Choose another time or resource.`}
          role="status"
        />
      ) : null}
      {!resource ? (
        <DataState state="empty" title="Select a resource" message="Choose a resource card on the left before checking availability or reserving." className="mt-4" />
      ) : null}
      {resource && !availabilityQuery.isLoading ? (
        <AvailabilityDetailCard
          resource={bookingResource}
          resourceTypes={resourceTypes}
          usePeriods={usePeriodBookings}
          usePeriodsLoading={usePeriodsQuery.isLoading}
          usePeriodsUpdating={usePeriodsQuery.isFetching && !usePeriodsQuery.isLoading}
          returningBookingId={returnMutation.variables}
          cancellingBookingId={cancelMutation.variables}
          onReturn={(bookingId) => returnMutation.mutate(bookingId)}
          onCancel={(bookingId) => cancelMutation.mutate(bookingId)}
        />
      ) : null}
      {(returnMutation.error || cancelMutation.error) ? (
        <DataState
          state="error"
          title="Use period update failed"
          message={(returnMutation.error ?? cancelMutation.error)?.message ?? 'Unable to update this use period.'}
          className="mt-4"
        />
      ) : null}
      {resource ? (
        <div className="mt-4">
          <BookingForm
            key={`${resource.id}-${startsAt}-${endsAt}`}
            resources={bookingResource ? [bookingResource] : []}
            resourceTypes={resourceTypes}
            defaultStartsAt={startsAt}
            defaultEndsAt={endsAt}
            disabled={!hasValidWindow}
          />
        </div>
      ) : null}
    </section>
  );
}

function AvailabilityDetailCard({
  resource,
  resourceTypes,
  usePeriods,
  usePeriodsLoading,
  usePeriodsUpdating,
  returningBookingId,
  cancellingBookingId,
  onReturn,
  onCancel,
}: {
  resource: ResourceItem | undefined;
  resourceTypes: ResourceType[];
  usePeriods: Booking[];
  usePeriodsLoading: boolean;
  usePeriodsUpdating: boolean;
  returningBookingId?: number;
  cancellingBookingId?: number;
  onReturn: (bookingId: number) => void;
  onCancel: (bookingId: number) => void;
}) {
  if (!resource) {
    return <DataState state="empty" title="No availability data" message="Availability for the selected resource has not been returned yet." />;
  }
  const resourceType = resourceTypes.find((type) => type.id === resource.resourceTypeId)?.name ?? resource.resourceType ?? `Type #${resource.resourceTypeId}`;
  const conflicts = resource.conflictingBookingCount ?? 0;
  const available = (resource.availableQuantity ?? resource.totalQuantity) > 0;
  const availableQuantity = resource.availableQuantity ?? resource.totalQuantity;
  const allocatedQuantity = resource.allocatedQuantity ?? Math.max(resource.totalQuantity - availableQuantity, 0);
  const statusLabel = available ? `${availableQuantity} available` : 'Unavailable';
  return (
    <section className="mt-4 rounded-lg border border-border/70 bg-muted/20 p-3" aria-label="Selected resource availability">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-base font-bold">{resource.name}</h3>
          <p className="text-sm text-muted-foreground">{resourceType} · {resource.location ?? 'No location'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {availableQuantity} available · {allocatedQuantity} allocated · {resource.totalQuantity} total
          </p>
        </div>
        <span className={`status-pill ${available ? 'available' : 'unavailable'}`}>
          {statusLabel}
          {conflicts ? ` · ${conflicts} conflict${conflicts === 1 ? '' : 's'}` : ''}
        </span>
      </div>
      <div className="mt-3 rounded-md border bg-background p-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-sm font-bold">Use periods</h4>
          <div className="flex flex-wrap items-center gap-2">
            {usePeriodsUpdating ? <span className="text-xs text-muted-foreground" role="status">Updating…</span> : null}
            {usePeriods.length ? <Badge variant="secondary">{usePeriods.length} period{usePeriods.length === 1 ? '' : 's'}</Badge> : null}
          </div>
        </div>
        {usePeriodsLoading ? <DataState state="loading" message="Loading use periods." className="mt-2" /> : null}
        {!usePeriodsLoading && usePeriods.length ? (
          <ul className="mt-2 grid max-h-56 gap-2 overflow-y-auto pr-1">
            {usePeriods.map((period) => (
              <li key={period.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/40 p-2 text-sm">
                <span>{formatDateTime(period.startsAt)} – {formatDateTime(period.endsAt)}</span>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">Qty {period.quantity}</Badge>
                  <StatusBadge status={period.status} />
                  {canReturnBooking(period) ? (
                    <Button type="button" size="sm" onClick={() => onReturn(period.id)} disabled={returningBookingId === period.id}>
                      Return resource
                    </Button>
                  ) : null}
                  {canCancelFutureBooking(period) ? (
                    <Button type="button" size="sm" variant="outline" onClick={() => onCancel(period.id)} disabled={cancellingBookingId === period.id}>
                      Cancel
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        {!usePeriodsLoading && !usePeriods.length ? (
          <p className="mt-2 text-sm text-muted-foreground">No use periods for this resource.</p>
        ) : null}
        {conflicts ? <p className="mt-2 text-xs text-muted-foreground">{conflicts} overlapping booking{conflicts === 1 ? '' : 's'} found in this window.</p> : null}
      </div>
    </section>
  );
}

function canReturnBooking(booking: Booking) {
  const now = Date.now();
  return ['confirmed', 'reserved'].includes(booking.status)
    && new Date(booking.startsAt).getTime() <= now
    && now < new Date(booking.endsAt).getTime();
}

function canCancelFutureBooking(booking: Booking) {
  return ['pending', 'confirmed', 'reserved'].includes(booking.status)
    && new Date(booking.startsAt).getTime() > Date.now();
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
