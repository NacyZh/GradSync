import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BellRing, Save } from 'lucide-react';

import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { useAppFeedback } from '@/shared/ui/AppFeedback';
import {
  getProjectNotificationPolicy,
  notificationQueryKeys,
  updateProjectNotificationPolicy,
} from '../notifications';

export function ProjectNotificationPolicy({ projectId }: { projectId: number }) {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: notificationQueryKeys.projectPolicy(projectId),
    queryFn: () => getProjectNotificationPolicy(projectId),
  });
  const [values, setValues] = useState({
    reminderLeadMinutes: 1440,
    escalationDelayMinutes: 1440,
    repeatIntervalMinutes: 1440,
    maxReminders: 3,
  });

  useEffect(() => {
    if (!query.data) return;
    setValues({
      reminderLeadMinutes: query.data.reminderLeadMinutes,
      escalationDelayMinutes: query.data.escalationDelayMinutes,
      repeatIntervalMinutes: query.data.repeatIntervalMinutes,
      maxReminders: query.data.maxReminders,
    });
  }, [query.data]);

  const mutation = useMutation({
    mutationFn: () => updateProjectNotificationPolicy(projectId, {
      expectedVersion: query.data?.version ?? 0,
      ...values,
    }),
    onSuccess: (policy) => {
      queryClient.setQueryData(notificationQueryKeys.projectPolicy(projectId), policy);
      notify(t('projectNotificationPolicySaved'), 'success');
    },
    onError: (error) => {
      notify(error.message, 'error');
    },
  });

  if (!query.data?.capabilities.canEdit) return null;
  const minimum = query.data.bounds?.minimumMinutes ?? 60;
  const maximum = query.data.bounds?.maximumMinutes ?? 10080;
  return (
    <section className="panel" aria-labelledby="project-notification-policy-heading">
      <div className="mb-4">
        <h2 id="project-notification-policy-heading" className="flex items-center gap-2">
          <BellRing className="h-4 w-4" aria-hidden="true" />
          {t('projectNotificationPolicy')}
        </h2>
        <p className="text-sm text-muted-foreground">{t('projectNotificationPolicyDescription')}</p>
      </div>
      <form
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (
            values.reminderLeadMinutes < minimum
            || values.reminderLeadMinutes > maximum
            || values.escalationDelayMinutes < minimum
            || values.escalationDelayMinutes > maximum
            || values.repeatIntervalMinutes < minimum
            || values.repeatIntervalMinutes > maximum
            || values.maxReminders < 0
            || values.maxReminders > 20
          ) {
            notify(t('notificationPolicyRangeError'), 'error');
            return;
          }
          mutation.mutate();
        }}
      >
        <PolicyInput label={t('reminderLeadMinutes')} value={values.reminderLeadMinutes} min={minimum} max={maximum} onChange={(value) => setValues((current) => ({ ...current, reminderLeadMinutes: value }))} />
        <PolicyInput label={t('escalationDelayMinutes')} value={values.escalationDelayMinutes} min={minimum} max={maximum} onChange={(value) => setValues((current) => ({ ...current, escalationDelayMinutes: value }))} />
        <PolicyInput label={t('repeatIntervalMinutes')} value={values.repeatIntervalMinutes} min={minimum} max={maximum} onChange={(value) => setValues((current) => ({ ...current, repeatIntervalMinutes: value }))} />
        <PolicyInput label={t('maximumReminders')} value={values.maxReminders} min={0} max={20} onChange={(value) => setValues((current) => ({ ...current, maxReminders: value }))} />
        <Button className="w-fit sm:col-span-2 xl:col-span-4" type="submit" disabled={mutation.isPending}>
          <Save className="h-4 w-4" aria-hidden="true" />
          {mutation.isPending ? t('saving') : t('save')}
        </Button>
      </form>
    </section>
  );
}

function PolicyInput({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return (
    <label className="grid gap-1 text-sm font-bold">
      {label}
      <Input type="number" value={value} min={min} max={max} onChange={(event) => onChange(Number(event.target.value))} required />
    </label>
  );
}
