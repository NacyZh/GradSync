import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { AsyncState } from '../../shared/ui/AsyncState';
import { NotificationList } from '../notifications/NotificationList';
import { BookingActions } from './BookingActions';
import { BookingCalendar } from './BookingCalendar';
import { BookingForm } from './BookingForm';
import { listBookings, listResources } from './api';

export function ResourceListPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const [query, setQuery] = useState('');
  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: listResources });
  const bookingsQuery = useQuery({ queryKey: ['bookings', projectId], queryFn: () => listBookings(projectId), enabled: Boolean(projectId) });
  const resources = resourcesQuery.data?.results ?? [];
  const filteredResources = useMemo(
    () => resources.filter((resource) => `${resource.name} ${resource.resource_type} ${resource.location ?? ''}`.toLowerCase().includes(query.toLowerCase())),
    [query, resources],
  );

  return (
    <section className="resource-workspace">
      <div className="page-heading">
        <div>
          <h1>Lab resources</h1>
          <p>Search availability, reserve equipment or seats, and manage future bookings.</p>
        </div>
      </div>
      <label className="search-field">
        Search resources
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Equipment, seat, room" />
      </label>
      <div className="two-column-workspace">
        <section className="panel" aria-label="Resource list">
          <h2>Resources</h2>
          {resourcesQuery.isLoading ? <AsyncState state="loading" message="Loading resources" /> : null}
          {filteredResources.length === 0 && !resourcesQuery.isLoading ? <AsyncState state="empty" message="No resources match this search." /> : null}
          <ul className="resource-list">
            {filteredResources.map((resource) => (
              <li key={resource.id}>
                <div>
                  <strong>{resource.name}</strong>
                  <p>{resource.resource_type} · {resource.location ?? 'No location'}</p>
                </div>
                <span className={`status-pill ${resource.status}`}>{resource.status}</span>
              </li>
            ))}
          </ul>
        </section>
        <BookingCalendar />
      </div>
      {projectId ? <BookingForm projectId={projectId} resources={filteredResources} /> : null}
      {projectId ? (
        <section className="panel" aria-label="Upcoming booking actions">
          <h2>Upcoming bookings</h2>
          {bookingsQuery.data?.results.length === 0 ? <AsyncState state="empty" message="No future bookings for this project." /> : null}
          <ul className="resource-list">
            {bookingsQuery.data?.results.map((booking) => (
              <li key={booking.id}>
                <div>
                  <strong>Booking #{booking.id}</strong>
                  <p>{booking.starts_at} to {booking.ends_at}</p>
                </div>
                <BookingActions projectId={projectId} bookingId={booking.id} startsAt={booking.starts_at} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {projectId ? <NotificationList projectId={projectId} /> : null}
    </section>
  );
}
