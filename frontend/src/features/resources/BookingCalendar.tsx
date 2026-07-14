import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Filter, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { DataState } from '../../shared/ui/DataState';
import { BookingConflictAlert } from './BookingConflictAlert';
import { BookingForm } from './BookingForm';
import type { LaboratoryResource, ResourceItem, ResourceType } from './api';
import { listResourceAvailability } from './api';

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
  const availability = useMemo(() => availabilityQuery.data?.results ?? [], [availabilityQuery.data]);
  const selectedAvailability = availability.find((item) => item.id === resource?.id);
  const bookingResource = selectedAvailability ?? (resource ? {
    ...resource,
    status: resource.status === 'active' ? 'available' : resource.status,
  } : undefined);
  const availableQuantity = bookingResource ? bookingResource.availableQuantity ?? bookingResource.totalQuantity : 0;
  const isUnavailable = Boolean(bookingResource && availableQuantity < 1);
  const observedAt = availabilityQuery.data?.observedAt;

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
      {resource && !availabilityQuery.isLoading ? <AvailabilityDetailCard resource={bookingResource} resourceTypes={resourceTypes} /> : null}
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

function AvailabilityDetailCard({ resource, resourceTypes }: { resource: ResourceItem | undefined; resourceTypes: ResourceType[] }) {
  if (!resource) {
    return <DataState state="empty" title="No availability data" message="Availability for the selected resource has not been returned yet." />;
  }
  const resourceType = resourceTypes.find((type) => type.id === resource.resourceTypeId)?.name ?? resource.resourceType ?? `Type #${resource.resourceTypeId}`;
  const conflicts = resource.conflictingBookingCount ?? 0;
  const available = (resource.availableQuantity ?? resource.totalQuantity) > 0;
  const availableQuantity = resource.availableQuantity ?? resource.totalQuantity;
  const allocatedQuantity = resource.allocatedQuantity ?? Math.max(resource.totalQuantity - availableQuantity, 0);
  const statusLabel = available ? `${availableQuantity} available` : 'Unavailable';
  const usePeriods = resource.currentUsePeriods ?? [];

  return (
    <section className="mt-4 rounded-lg border border-border/70 bg-muted/20 p-4" aria-label="Selected resource availability">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-bold">{resource.name}</h3>
          <p className="text-sm text-muted-foreground">{resourceType} · {resource.location ?? 'No location'}</p>
        </div>
        <span className={`status-pill ${available ? 'available' : 'unavailable'}`}>
          {statusLabel}
          {conflicts ? ` · ${conflicts} conflict${conflicts === 1 ? '' : 's'}` : ''}
        </span>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-md border bg-background p-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Available</dt>
          <dd className="mt-1 text-xl font-extrabold">{availableQuantity}</dd>
        </div>
        <div className="rounded-md border bg-background p-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Allocated</dt>
          <dd className="mt-1 text-xl font-extrabold">{allocatedQuantity}</dd>
        </div>
        <div className="rounded-md border bg-background p-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Total</dt>
          <dd className="mt-1 text-xl font-extrabold">{resource.totalQuantity}</dd>
        </div>
      </dl>
      <div className="mt-4 rounded-md border bg-background p-3">
        <h4 className="text-sm font-bold">Current use periods</h4>
        {usePeriods.length ? (
          <ul className="mt-2 grid gap-2">
            {usePeriods.map((period) => (
              <li key={period.bookingId} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/40 p-2 text-sm">
                <span>{formatDateTime(period.startsAt)} – {formatDateTime(period.endsAt)}</span>
                <Badge variant="secondary">Qty {period.quantity}</Badge>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">No active use in the selected window.</p>
        )}
        {conflicts ? <p className="mt-2 text-xs text-muted-foreground">{conflicts} overlapping booking{conflicts === 1 ? '' : 's'} found in this window.</p> : null}
      </div>
    </section>
  );
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
