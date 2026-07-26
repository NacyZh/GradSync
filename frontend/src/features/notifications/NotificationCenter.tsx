import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { useI18n } from '@/shared/i18n/I18nProvider';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/primitives/dialog';

import { NotificationList } from './NotificationList';
import {
  listNotifications,
  markNotificationsRead,
  notificationQueryKey,
  notificationResults,
  type NotificationResponse,
} from './api';

export function NotificationCenter() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const notificationsQuery = useQuery({
    queryKey: notificationQueryKey,
    queryFn: () => listNotifications(),
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
  const notifications = notificationResults(notificationsQuery.data);
  const unreadNotifications = notifications.filter((notification) => !notification.readAt);
  const unreadCount = Array.isArray(notificationsQuery.data)
    ? unreadNotifications.length
    : notificationsQuery.data?.unreadCount ?? unreadNotifications.length;
  const pendingActionCount = Array.isArray(notificationsQuery.data)
    ? notifications.filter((notification) => notification.activeFollowUp).length
    : notificationsQuery.data?.pendingActionCount ?? 0;
  const markedIds = useRef(new Set<number>());
  const markReadMutation = useMutation({
    mutationFn: markNotificationsRead,
    onError: () => queryClient.invalidateQueries({ queryKey: notificationQueryKey }),
  });

  useEffect(() => {
    if (!open || unreadNotifications.length === 0 || markReadMutation.isPending) return;
    const loadedIds = unreadNotifications
      .map((notification) => notification.id)
      .filter((id) => !markedIds.current.has(id));
    if (!loadedIds.length) return;
    loadedIds.forEach((id) => markedIds.current.add(id));
    const readAt = new Date().toISOString();
    queryClient.setQueryData<NotificationResponse>(notificationQueryKey, (current) => {
      if (!current) return current;
      const markRead = (notification: (typeof notifications)[number]) => (
        loadedIds.includes(notification.id) ? { ...notification, readAt } : notification
      );
      return Array.isArray(current)
        ? current.map(markRead)
        : { ...current, results: current.results.map(markRead) };
    });
    markReadMutation.mutate(loadedIds);
  }, [markReadMutation, notifications, open, queryClient, unreadNotifications]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="icon" className="notification-button" type="button" aria-label={t('openNotifications')}>
          <Bell className="h-4 w-4" aria-hidden="true" />
          {unreadCount > 0 ? <span className="unread-dot" data-testid="notification-unread-dot" aria-hidden="true" /> : null}
          <span className="sr-only" aria-live="polite">
            {unreadCount > 0 ? t('unreadNotifications', { count: unreadCount }) : t('noUnreadNotifications')}
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent className="notification-drawer">
        <DialogTitle className="sr-only">{t('notifications')}</DialogTitle>
        <DialogDescription className="sr-only">
          {t('notificationDescription')}
        </DialogDescription>
        <NotificationList compact pendingActionCount={pendingActionCount} />
      </DialogContent>
    </Dialog>
  );
}
