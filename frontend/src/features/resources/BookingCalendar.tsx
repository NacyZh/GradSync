import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { listResourceAvailability } from './api';

function toDateTimeLocal(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

export function BookingCalendar() {
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
  const availabilityQuery = useQuery({
    queryKey: ['resource-availability', startsAt, endsAt],
    queryFn: () => listResourceAvailability(startsAt, endsAt),
    enabled: Boolean(startsAt && endsAt),
  });

  return (
    <section aria-label="Booking calendar">
      <h2>Availability</h2>
      <label>
        Availability start
        <input name="availabilityStartsAt" type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} />
      </label>
      <label>
        Availability end
        <input name="availabilityEndsAt" type="datetime-local" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} />
      </label>
      <ul>
        {availabilityQuery.data?.map((resource) => (
          <li key={resource.id}>
            {resource.name}: {resource.available ? 'Available' : 'Unavailable'}
            {resource.conflicting_booking_count ? ` (${resource.conflicting_booking_count} conflict)` : ''}
          </li>
        ))}
      </ul>
    </section>
  );
}
