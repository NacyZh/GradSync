import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BellRing, Save } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { useI18n } from '@/shared/i18n/I18nProvider';

import {
  getNotificationPreferences,
  notificationQueryKeys,
  updateNotificationPreferences,
  type NotificationCategory,
} from './api';

const categoryKeys = {
  security: 'notificationCategory_security',
  project: 'notificationCategory_project',
  deliverable: 'notificationCategory_deliverable',
  report: 'notificationCategory_report',
  decision: 'notificationCategory_decision',
  risk: 'notificationCategory_risk',
  schedule: 'notificationCategory_schedule',
  administration: 'notificationCategory_administration',
} as const;

export function NotificationPreferences() {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: notificationQueryKeys.preferences,
    queryFn: getNotificationPreferences,
  });
  const [quietEnabled, setQuietEnabled] = useState(false);
  const [quietStart, setQuietStart] = useState('22:00');
  const [quietEnd, setQuietEnd] = useState('07:00');
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const [categoryEmail, setCategoryEmail] = useState<Partial<Record<NotificationCategory, boolean>>>({});

  useEffect(() => {
    if (!query.data || !Array.isArray(query.data.categories)) return;
    setQuietEnabled(query.data.quietHoursEnabled);
    setQuietStart(query.data.quietHoursStart?.slice(0, 5) || '22:00');
    setQuietEnd(query.data.quietHoursEnd?.slice(0, 5) || '07:00');
    setTimezone(query.data.timezone);
    setCategoryEmail(Object.fromEntries(
      query.data.categories.map((item) => [item.category, item.emailEnabled]),
    ));
  }, [query.data]);

  const mutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: (preferences) => {
      queryClient.setQueryData(notificationQueryKeys.preferences, preferences);
      notify(t('notificationPreferencesSaved'), 'success');
    },
    onError: (error) => {
      notify(error.message, 'error');
    },
  });

  if (!query.data || !Array.isArray(query.data.categories)) return null;
  return (
    <section className="panel max-w-3xl" aria-labelledby="notification-preferences-heading">
      <div className="mb-5">
        <h2 id="notification-preferences-heading" className="flex items-center gap-2 text-base">
          <BellRing className="h-4 w-4" aria-hidden="true" />
          {t('notificationPreferences')}
        </h2>
        <p className="text-sm text-muted-foreground">{t('notificationPreferencesDescription')}</p>
      </div>
      <form
        className="grid gap-5"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate({
            expectedVersion: query.data.version,
            quietHoursEnabled: quietEnabled,
            quietHoursStart: quietEnabled ? quietStart : null,
            quietHoursEnd: quietEnabled ? quietEnd : null,
            timezone,
            categoryEmail,
          });
        }}
      >
        <label className="flex items-center gap-3 text-sm font-bold">
          <input type="checkbox" checked={quietEnabled} onChange={(event) => setQuietEnabled(event.target.checked)} />
          {t('enableQuietHours')}
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="grid gap-1 text-sm font-bold">
            {t('quietHoursStart')}
            <Input type="time" value={quietStart} disabled={!quietEnabled} onChange={(event) => setQuietStart(event.target.value)} />
          </label>
          <label className="grid gap-1 text-sm font-bold">
            {t('quietHoursEnd')}
            <Input type="time" value={quietEnd} disabled={!quietEnabled} onChange={(event) => setQuietEnd(event.target.value)} />
          </label>
          <label className="grid gap-1 text-sm font-bold">
            {t('timezone')}
            <Input value={timezone} onChange={(event) => setTimezone(event.target.value)} />
          </label>
        </div>
        <div className="grid gap-2" aria-label={t('notificationCategoryEmail')}>
          {query.data.categories.map((item) => (
            <label key={item.category} className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm">
              <span>
                <strong>{t(categoryKeys[item.category])}</strong>
                <span className="ml-2 text-muted-foreground">
                  {item.emailRequired ? t('mandatorySecurityDelivery') : t('emailDelivery')}
                </span>
              </span>
              <input
                type="checkbox"
                checked={item.emailRequired || Boolean(categoryEmail[item.category])}
                disabled={item.emailRequired}
                onChange={(event) => setCategoryEmail((current) => ({
                  ...current,
                  [item.category]: event.target.checked,
                }))}
              />
            </label>
          ))}
        </div>
        <p className="text-sm text-muted-foreground">{t('inAppAlwaysEnabled')}</p>
        <Button className="w-fit" type="submit" disabled={mutation.isPending}>
          <Save className="h-4 w-4" aria-hidden="true" />
          {mutation.isPending ? t('saving') : t('save')}
        </Button>
      </form>
    </section>
  );
}
