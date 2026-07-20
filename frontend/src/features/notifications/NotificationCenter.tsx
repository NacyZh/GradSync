import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
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
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const notificationsQuery = useQuery({
    queryKey: notificationQueryKey,
    queryFn: listNotifications,
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
  const notifications = notificationResults(notificationsQuery.data);
  const unreadNotifications = notifications.filter((notification) => !notification.readAt);
  const markReadMutation = useMutation({
    mutationFn: markNotificationsRead,
    onError: () => queryClient.invalidateQueries({ queryKey: notificationQueryKey }),
  });

  useEffect(() => {
    if (!open || unreadNotifications.length === 0 || markReadMutation.isPending) return;
    const throughId = Math.max(...unreadNotifications.map((notification) => notification.id));
    const readAt = new Date().toISOString();
    queryClient.setQueryData<NotificationResponse>(notificationQueryKey, (current) => {
      if (!current) return current;
      const markRead = (notification: (typeof notifications)[number]) => (
        notification.id <= throughId ? { ...notification, readAt } : notification
      );
      return Array.isArray(current)
        ? current.map(markRead)
        : { ...current, results: current.results.map(markRead) };
    });
    markReadMutation.mutate(throughId);
  }, [markReadMutation, notifications, open, queryClient, unreadNotifications]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="icon" className="notification-button" type="button" aria-label="Open notifications">
          <Bell className="h-4 w-4" aria-hidden="true" />
          {unreadNotifications.length > 0 ? <span className="unread-dot" data-testid="notification-unread-dot" aria-hidden="true" /> : null}
          <span className="sr-only" aria-live="polite">
            {unreadNotifications.length > 0 ? `${unreadNotifications.length} unread notifications` : 'No unread notifications'}
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent className="notification-drawer">
        <DialogTitle className="sr-only">Notifications</DialogTitle>
        <DialogDescription className="sr-only">
          Recent workspace notifications and delivery status.
        </DialogDescription>
        <NotificationList compact />
      </DialogContent>
    </Dialog>
  );
}
