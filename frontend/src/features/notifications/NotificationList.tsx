import { useQuery } from '@tanstack/react-query';

import { listProjectNotifications } from './api';

export function NotificationList({ projectId }: { projectId?: number }) {
  const notificationsQuery = useQuery({
    queryKey: ['notifications', projectId],
    queryFn: () => listProjectNotifications(projectId ?? 0),
    enabled: Boolean(projectId),
  });

  return (
    <section className="panel notification-center" aria-labelledby="notifications-heading">
      <h2 id="notifications-heading">Notifications</h2>
      {notificationsQuery.isLoading ? <p className="muted">Loading delivery status...</p> : null}
      {notificationsQuery.data?.results.length ? null : <p>No notifications loaded.</p>}
      <ul className="notification-list">
        {notificationsQuery.data?.results.map((notification) => (
          <li key={notification.id}>
            <span className={`status-dot ${notification.status}`} aria-hidden="true" />
            <div>
              <strong>{notification.subject}</strong>
              <p>{notification.event_type ?? notification.target_type} · {notification.status}</p>
              {notification.action_path ? <a href={notification.action_path}>Open record</a> : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
