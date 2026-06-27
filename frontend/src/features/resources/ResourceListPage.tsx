import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import { BookingCalendar } from './BookingCalendar';
import { BookingForm } from './BookingForm';
import { listResources } from './api';

export function ResourceListPage() {
  const projectId = Number(useParams().projectId ?? 0);
  const resourcesQuery = useQuery({ queryKey: ['resources'], queryFn: listResources });

  return (
    <section>
      <h1>Lab resources</h1>
      <ul>
        {resourcesQuery.data?.results.map((resource) => (
          <li key={resource.id}>
            {resource.name} ({resource.status})
          </li>
        ))}
      </ul>
      <BookingCalendar />
      {projectId ? <BookingForm projectId={projectId} resources={resourcesQuery.data?.results ?? []} /> : null}
    </section>
  );
}
