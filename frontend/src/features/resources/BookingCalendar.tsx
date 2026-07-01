import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Filter } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DataState } from '../../shared/ui/DataState';
import { BookingConflictAlert } from './BookingConflictAlert';
import type { LabResource } from './api';
import { listResourceAvailability } from './api';

function toDateTimeLocal(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

type BookingCalendarProps = {
  onWindowChange?: (window: { startsAt: string; endsAt: string; hasValidWindow: boolean }) => void;
};

export function BookingCalendar({ onWindowChange }: BookingCalendarProps) {
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
  });
  const availability = availabilityQuery.data ?? [];
  const unavailable = availability.filter((resource) => !resource.available);

  function updateWindow(nextStartsAt = startsAt, nextEndsAt = endsAt) {
    const nextStartsAtMs = new Date(nextStartsAt).getTime();
    const nextEndsAtMs = new Date(nextEndsAt).getTime();
    onWindowChange?.({
      startsAt: nextStartsAt,
      endsAt: nextEndsAt,
      hasValidWindow: Number.isFinite(nextStartsAtMs) && Number.isFinite(nextEndsAtMs) && nextStartsAtMs > Date.now() && nextEndsAtMs > nextStartsAtMs,
    });
  }

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
        <Badge variant="secondary">
          <Filter className="h-3.5 w-3.5" aria-hidden="true" />
          {availability.length} resources
        </Badge>
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
      {availabilityQuery.error ? <DataState state="error" title="Availability unavailable" message={availabilityQuery.error.message} className="mt-4" /> : null}
      {unavailable.length ? (
        <BookingConflictAlert
          title="Conflicts in this window"
          message={`${unavailable.length} resource${unavailable.length === 1 ? '' : 's'} already have overlapping project bookings. Choose another time or resource.`}
          role="status"
        />
      ) : null}
      {hasValidWindow && !availabilityQuery.isLoading && !availabilityQuery.error && availability.length === 0 ? (
        <DataState state="empty" title="No availability data" message="No resources are available for this search window." className="mt-4" />
      ) : null}
      <ul className="resource-list mt-4">
        {availability.map((resource) => (
          <AvailabilityRow key={resource.id} resource={resource} />
        ))}
      </ul>
    </section>
  );
}

function AvailabilityRow({ resource }: { resource: LabResource }) {
  const conflicts = resource.conflicting_booking_count ?? 0;
  const statusLabel = resource.available ? 'Available' : 'Unavailable';

  return (
    <li>
      <div className="min-w-0">
        <strong>{resource.name}</strong>
        <p>
          {resource.resource_type} · {resource.location ?? 'No location'}
        </p>
        {conflicts ? <small className="text-muted-foreground">{conflicts} overlapping booking{conflicts === 1 ? '' : 's'}</small> : null}
      </div>
      <span className={`status-pill ${resource.available ? 'available' : 'unavailable'}`}>
        {statusLabel}
        {conflicts ? ` · ${conflicts} conflict${conflicts === 1 ? '' : 's'}` : ''}
      </span>
    </li>
  );
}
