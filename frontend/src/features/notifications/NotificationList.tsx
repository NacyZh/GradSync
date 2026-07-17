import { useQuery } from '@tanstack/react-query';
import { AlertCircle, BellRing, ExternalLink, MailCheck, RotateCcw } from 'lucide-react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { cn } from '@/shared/lib/utils';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { NotificationRecord } from './api';
import { listNotifications, listProjectNotifications } from './api';

export function NotificationList({ projectId, compact = false }: { projectId?: number; compact?: boolean }) {
  const notificationsQuery = useQuery({
    queryKey: ['notifications', projectId],
    queryFn: async () => {
      if (projectId) return listProjectNotifications(projectId);
      const response = await listNotifications();
      return Array.isArray(response) ? { results: response } : response;
    },
  });
  const notifications = notificationsQuery.data?.results ?? [];
  const failedCount = notifications.filter((notification) => notification.status === 'failed' || notification.status === 'retry_needed').length;
  const pendingCount = notifications.filter((notification) => notification.status === 'pending' || notification.status === 'queued').length;
  const skippedCount = notifications.filter((notification) => notification.status === 'skipped').length;

  return (
    <section className={cn('panel notification-center', compact && 'rounded-md border-0 shadow-none')} aria-labelledby="notifications-heading">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="notifications-heading" className="flex items-center gap-2">
            <BellRing className="h-4 w-4" aria-hidden="true" />
            Notifications
          </h2>
          <p className="text-sm text-muted-foreground">Project-scoped delivery status, action paths, and retry visibility.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={failedCount ? 'destructive' : 'muted'}>{failedCount} needs retry</Badge>
          <Badge variant={pendingCount ? 'warning' : 'muted'}>{pendingCount} pending</Badge>
          <Badge variant={skippedCount ? 'warning' : 'muted'}>{skippedCount} skipped</Badge>
        </div>
      </div>
      {notificationsQuery.isLoading ? <DataState state="loading" message="Loading delivery status." /> : null}
      {notificationsQuery.error ? <DataState state="error" title="Notifications unavailable" message={notificationsQuery.error.message} /> : null}
      {!notificationsQuery.isLoading && !notificationsQuery.error && notifications.length === 0 ? (
        <DataState state="empty" title="No notifications" message="No delivery records are loaded." />
      ) : null}
      <ul className={cn('notification-list', compact && 'max-h-[26rem] overflow-auto')}>
        {notifications.map((notification) => (
          <NotificationRow key={notification.id} notification={notification} />
        ))}
      </ul>
    </section>
  );
}

function NotificationRow({ notification }: { notification: NotificationRecord }) {
  const eventType = notification.event_type ?? notification.eventType;
  const targetType = notification.target_type ?? notification.targetType ?? notification.relatedObjectType;
  const targetId = notification.target_id ?? notification.targetId ?? notification.relatedObjectId;
  const projectId = notification.project_id ?? notification.projectId;
  const actionPath = notification.action_path ?? notification.actionPath;
  const eligibleAt = notification.eligible_at ?? notification.eligibleAt;
  const sentAt = notification.sent_at ?? notification.sentAt;
  const lastAttemptAt = notification.last_attempt_at ?? notification.lastAttemptAt;
  const retryCount = notification.retry_count ?? notification.retryCount ?? 0;
  const reason = notification.failure_reason ?? notification.failureReason ?? notification.skipped_reason ?? notification.skippedReason;
  const retryAllowed = notification.status === 'failed' || notification.status === 'retry_needed';

  return (
    <li className="items-start">
      <span className={`status-dot ${notification.status}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <strong className="min-w-0 truncate">{notification.subject}</strong>
          <StatusBadge status={notification.status} />
        </div>
        <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="font-bold text-muted-foreground">Event</dt>
            <dd>{formatToken(eventType ?? targetType ?? 'notification')}</dd>
          </div>
          <div>
            <dt className="font-bold text-muted-foreground">Project</dt>
            <dd>{projectId ? `Project #${projectId}` : 'Current project'}</dd>
          </div>
          <div>
            <dt className="font-bold text-muted-foreground">Target</dt>
            <dd>{formatToken(targetType ?? 'record')} #{targetId ?? 'unknown'}</dd>
          </div>
          <div>
            <dt className="font-bold text-muted-foreground">Delivery</dt>
            <dd>{sentAt ? `Sent ${formatDateTime(sentAt)}` : `Eligible ${formatDateTime(eligibleAt)}`}</dd>
          </div>
        </dl>
        {reason ? (
          <p className="mt-3 inline-flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
            <AlertCircle className="mt-0.5 h-4 w-4" aria-hidden="true" />
            {reason}
          </p>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-2">
          {actionPath ? (
            <Button asChild variant="outline" size="sm">
              <a href={actionPath}>
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Open record
              </a>
            </Button>
          ) : null}
          {retryAllowed ? (
            <Button type="button" variant="outline" size="sm" disabled title="Retry is handled by the delivery worker">
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              {notification.status === 'retry_needed' ? `Retry needed${retryCount ? ` (${retryCount})` : ''}` : 'Retry queued by worker'}
            </Button>
          ) : (
            <Badge variant="muted">
              <MailCheck className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              {notification.status === 'sent' ? 'Delivered' : notification.status === 'skipped' ? 'Skipped' : 'Worker monitored'}
            </Badge>
          )}
          {lastAttemptAt ? <Badge variant="muted">Last attempt {formatDateTime(lastAttemptAt)}</Badge> : null}
        </div>
      </div>
    </li>
  );
}

function formatToken(value: string) {
  return value.replaceAll('_', ' ');
}

function formatDateTime(value?: string | null) {
  if (!value) return 'not scheduled';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}
