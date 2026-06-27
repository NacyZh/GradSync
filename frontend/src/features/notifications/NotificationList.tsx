import { useQuery } from '@tanstack/react-query';

import { listProjectNotifications } from './api';

export function NotificationList({ projectId }: { projectId?: number }) {
  const notificationsQuery = useQuery({
    queryKey: ['notifications', projectId],
    queryFn: () => listProjectNotifications(projectId ?? 0),
    enabled: Boolean(projectId),
  });

  return (
    <section aria-labelledby="notifications-heading">
      <h2 id="notifications-heading">Notifications</h2>
      {notificationsQuery.data?.results.length ? null : <p>No notifications loaded.</p>}
      <ul>
        {notificationsQuery.data?.results.map((notification) => (
          <li key={notification.id}>
            {notification.subject} ({notification.status})
          </li>
        ))}
      </ul>
    </section>
  );
}
