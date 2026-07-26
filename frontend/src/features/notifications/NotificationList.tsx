import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, BellRing, Check, ExternalLink, MailCheck, RotateCcw } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import { cn } from '@/shared/lib/utils';
import { formatUiDate } from '@/shared/i18n/translate';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import { useAppFeedback } from '../../shared/ui/AppFeedback';
import { useI18n } from '../../shared/i18n/I18nProvider';
import type { NotificationRecord } from './api';
import {
  acknowledgeNotification,
  listNotifications,
  listProjectNotifications,
  notificationQueryKey,
  notificationResults,
  type NotificationCategory,
  type NotificationOutcome,
} from './api';

const categoryMessageKeys = {
  security: 'notificationCategory_security',
  project: 'notificationCategory_project',
  deliverable: 'notificationCategory_deliverable',
  report: 'notificationCategory_report',
  decision: 'notificationCategory_decision',
  risk: 'notificationCategory_risk',
  schedule: 'notificationCategory_schedule',
  administration: 'notificationCategory_administration',
} as const;

const outcomeMessageKeys = {
  not_required: 'notificationOutcome_not_required',
  pending: 'notificationOutcome_pending',
  acknowledged: 'notificationOutcome_acknowledged',
  completed: 'notificationOutcome_completed',
  expired: 'notificationOutcome_expired',
  unavailable: 'notificationOutcome_unavailable',
} as const;

export function NotificationList({ projectId, compact = false, pendingActionCount }: { projectId?: number; compact?: boolean; pendingActionCount?: number }) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const queryClient = useQueryClient();
  const [category, setCategory] = useState<NotificationCategory | ''>('');
  const [outcome, setOutcome] = useState<NotificationOutcome | ''>('');
  const filtered = Boolean(category || outcome);
  const notificationsQuery = useQuery({
    queryKey: projectId
      ? ['notifications', projectId]
      : filtered
        ? [...notificationQueryKey, category, outcome]
        : notificationQueryKey,
    queryFn: async () => {
      if (projectId) return listProjectNotifications(projectId);
      const response = await listNotifications(
        filtered
          ? { category: category || undefined, outcome: outcome || undefined, pageSize: 100 }
          : {},
      );
      return Array.isArray(response) ? { results: response } : response;
    },
  });
  const notifications = projectId
    ? (notificationsQuery.data as { results: NotificationRecord[] } | undefined)?.results ?? []
    : notificationResults(notificationsQuery.data);
  const failedCount = notifications.filter((notification) => notification.status === 'failed' || notification.status === 'retry_needed').length;
  const pendingCount = notifications.filter((notification) => notification.status === 'pending' || notification.status === 'queued').length;
  const skippedCount = notifications.filter((notification) => notification.status === 'skipped').length;
  const visiblePendingActions = pendingActionCount ?? notifications.filter(
    (notification) => notification.activeFollowUp && notification.outcomeState === 'pending',
  ).length;
  const acknowledgeMutation = useMutation({
    mutationFn: acknowledgeNotification,
    onSuccess: () => {
      notify(t('notificationAcknowledged'), 'success');
      queryClient.invalidateQueries({ queryKey: notificationQueryKey });
    },
    onError: (error) => notify(error.message, 'error'),
  });

  return (
    <section className={cn('panel notification-center', compact && 'notification-drawer-center')} aria-labelledby="notifications-heading">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="notifications-heading" className="flex items-center gap-2">
            <BellRing className="h-4 w-4" aria-hidden="true" />
            {t('notifications')}
          </h2>
          <p className="text-sm text-muted-foreground">{t('notificationDescription')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={failedCount ? 'destructive' : 'muted'}>{failedCount} needs retry</Badge>
          <Badge variant={pendingCount ? 'warning' : 'muted'}>{pendingCount} pending</Badge>
          <Badge variant={skippedCount ? 'warning' : 'muted'}>{skippedCount} skipped</Badge>
          <Badge variant={visiblePendingActions ? 'warning' : 'muted'}>
            {t('pendingActions', { count: visiblePendingActions })}
          </Badge>
        </div>
      </div>
      {!projectId ? (
        <div className="mb-4 grid gap-2 sm:grid-cols-2" aria-label={t('notificationFilters')}>
          <label className="grid gap-1 text-sm font-bold">
            {t('category')}
            <select className="input" value={category} onChange={(event) => setCategory(event.target.value as NotificationCategory | '')}>
              <option value="">{t('all')}</option>
              {(['security', 'project', 'deliverable', 'report', 'decision', 'risk', 'schedule', 'administration'] as NotificationCategory[]).map((value) => (
                <option key={value} value={value}>{t(categoryMessageKeys[value])}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-bold">
            {t('notificationOutcome')}
            <select className="input" value={outcome} onChange={(event) => setOutcome(event.target.value as NotificationOutcome | '')}>
              <option value="">{t('all')}</option>
              {(['pending', 'acknowledged', 'completed', 'expired', 'unavailable'] as NotificationOutcome[]).map((value) => (
                <option key={value} value={value}>{t(outcomeMessageKeys[value])}</option>
              ))}
            </select>
          </label>
        </div>
      ) : null}
      {notificationsQuery.isLoading ? <DataState state="loading" message="Loading delivery status." /> : null}
      {notificationsQuery.error ? <DataState state="error" title="Notifications unavailable" message={notificationsQuery.error.message} /> : null}
      {!notificationsQuery.isLoading && !notificationsQuery.error && notifications.length === 0 ? (
        <DataState state="empty" title="No notifications" message="No delivery records are loaded." />
      ) : null}
      <ul className={cn('notification-list', compact && 'notification-drawer-list')}>
        {notifications.map((notification) => (
          <NotificationRow
            key={notification.id}
            notification={notification}
            onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
            acknowledging={acknowledgeMutation.isPending}
          />
        ))}
      </ul>
    </section>
  );
}

function NotificationRow({ notification, onAcknowledge, acknowledging }: { notification: NotificationRecord; onAcknowledge: (id: number) => void; acknowledging: boolean }) {
  const { t } = useI18n();
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
  const deliveryPolicy = notification.delivery_policy ?? notification.deliveryPolicy;

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
          {notification.requirementType === 'acknowledgement' && notification.outcomeState === 'pending' ? (
            <Button type="button" size="sm" onClick={() => onAcknowledge(notification.id)} disabled={acknowledging}>
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
              {t('acknowledgeNotification')}
            </Button>
          ) : null}
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
          {deliveryPolicy ? (
            <Badge variant="muted">
              {deliveryPolicy === 'in_app'
                ? 'In-app only'
                : deliveryPolicy === 'email_only'
                  ? 'Email only'
                  : 'In-app + email'}
            </Badge>
          ) : null}
          {notification.outcomeState && notification.outcomeState !== 'not_required' ? (
            <Badge variant={notification.outcomeState === 'pending' ? 'warning' : 'muted'}>
              {t(outcomeMessageKeys[notification.outcomeState])}
            </Badge>
          ) : null}
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
  return formatUiDate(value, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}
