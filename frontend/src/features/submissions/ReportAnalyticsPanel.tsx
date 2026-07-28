import { Download } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { Button } from '@/shared/ui/primitives/button';
import { DataState } from '@/shared/ui/DataState';

import { downloadReportAnalytics, getReportAnalytics } from './api';

export function ReportAnalyticsPanel({ projectId, from, to }: { projectId: number; from: string; to: string }) {
  const { t, locale, formatNumber } = useI18n();
  const query = useQuery({
    queryKey: ['reportAnalytics', projectId, from, to],
    queryFn: () => getReportAnalytics(projectId, from, to),
    enabled: Boolean(projectId && from && to),
  });
  if (query.isLoading) return <DataState state="loading" message={t('loadingReportAnalytics')} />;
  if (query.error) return <DataState state="error" message={query.error.message} />;
  const data = query.data;
  if (!data) return <DataState state="empty" message={t('noReportAnalytics')} />;
  return (
    <section className="grid gap-4" aria-label={t('reportAnalytics')}>
      <div className="flex justify-end">
        <Button type="button" variant="outline" onClick={() => downloadReportAnalytics(projectId, from, to)}>
          <Download className="h-4 w-4" />{t('exportCsv')}
        </Button>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        {Object.entries(data.submissionCounts).map(([key, value]) => <div key={key} className="rounded-md border p-3"><div className="text-xs text-muted-foreground">{t(key === 'onTime' ? 'onTime' : key as 'expected' | 'late' | 'missing')}</div><strong>{formatNumber(value)}</strong></div>)}
      </div>
      <div className="max-h-[30rem] overflow-auto rounded-md border">
        <table className="w-full text-sm">
          <thead><tr><th className="p-3 text-left">{t('metric')}</th><th className="p-3 text-right">{t('value')}</th><th className="p-3 text-right">{t('population')}</th><th className="p-3 text-right">{t('missing')}</th></tr></thead>
          <tbody>{data.metricSeries.map((metric) => <tr key={metric.key} className="border-t"><td className="p-3">{locale === 'zh' ? metric.labelZh : metric.labelEn}</td><td className="p-3 text-right">{metric.value === null ? t('notAvailable') : formatNumber(metric.value)}</td><td className="p-3 text-right">{metric.population}</td><td className="p-3 text-right">{metric.missing}</td></tr>)}</tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">{t('analyticsNoRanking')}</p>
    </section>
  );
}
