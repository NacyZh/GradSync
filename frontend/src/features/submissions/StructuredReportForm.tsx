import { useState } from 'react';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Textarea } from '@/shared/ui/primitives/textarea';
import { useAppFeedback } from '@/shared/ui/AppFeedback';

import { type ReportingPeriod, type ReportTemplateVersion, submitStructuredReport } from './api';

export function StructuredReportForm({
  projectId,
  period,
  template,
  onSubmitted,
}: {
  projectId: number;
  period: ReportingPeriod;
  template: ReportTemplateVersion;
  onSubmitted: () => void;
}) {
  const { t, locale } = useI18n();
  const { notify } = useAppFeedback();
  const [values, setValues] = useState<Record<number, unknown>>({});
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      await submitStructuredReport(projectId, {
        reportingPeriodId: period.id,
        responses: template.fields.map((field) => ({ fieldId: field.id, value: values[field.id] ?? '' })),
        idempotencyKey: crypto.randomUUID(),
      });
      notify(t('structuredReportSubmitted'), 'success');
      onSubmitted();
    } catch (error) {
      notify(error instanceof Error ? error.message : t('structuredReportSubmitFailed'), 'error');
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="grid gap-4" onSubmit={submit} aria-label={t('structuredReportForm')}>
      {template.fields.map((field) => {
        const label = locale === 'zh' ? field.labelZh : field.labelEn;
        const value = values[field.id] ?? '';
        if (field.fieldType === 'long_text' || field.fieldType === 'risk_blocker') {
          return <label key={field.id} className="grid gap-1.5 text-sm font-medium">{label}<Textarea required={field.required} value={String(value)} onChange={(event) => setValues((current) => ({ ...current, [field.id]: event.target.value }))} /></label>;
        }
        return <label key={field.id} className="grid gap-1.5 text-sm font-medium">{label}<Input required={field.required} type={field.fieldType === 'number' || field.fieldType === 'percentage' ? 'number' : 'text'} min={field.minValue ?? undefined} max={field.maxValue ?? undefined} value={String(value)} onChange={(event) => setValues((current) => ({ ...current, [field.id]: event.target.value }))} /></label>;
      })}
      <Button type="submit" disabled={pending}>{t('submitReport')}</Button>
    </form>
  );
}
