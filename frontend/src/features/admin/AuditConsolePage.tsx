import { useMutation, useQuery } from '@tanstack/react-query';
import { Download, FileSearch, Filter, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useAppFeedback } from '@/shared/ui/AppFeedback';
import { DataState } from '@/shared/ui/DataState';
import { PageShell } from '@/shared/ui/PageShell';
import { Button } from '@/shared/ui/primitives/button';
import { Input } from '@/shared/ui/primitives/input';
import { Label } from '@/shared/ui/primitives/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/primitives/select';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { useI18n } from '@/shared/i18n/I18nProvider';

import { AuditEventDetail } from './AuditEventDetail';
import {
  createAuditExport,
  downloadAuditExport,
  getAuditEvent,
  getAuditExport,
  listAuditEvents,
  type AuditFilters,
} from './api';

export function AuditConsolePage() {
  const { t } = useI18n();
  const { notify } = useAppFeedback();
  const [params, setParams] = useSearchParams();
  const filters = useMemo<AuditFilters>(
    () => ({
      q: params.get('q') ?? '',
      category: params.get('category') ?? '',
      outcome: params.get('outcome') ?? '',
    }),
    [params],
  );
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [exportId, setExportId] = useState<string | null>(null);
  const eventsQuery = useQuery({
    queryKey: ['audit-events', filters],
    queryFn: () => listAuditEvents(filters),
  });
  const events = useMemo(
    () => eventsQuery.data?.results ?? [],
    [eventsQuery.data?.results],
  );
  useEffect(() => {
    if (!selectedId && events[0]) setSelectedId(events[0].id);
  }, [events, selectedId]);
  const detailQuery = useQuery({
    queryKey: ['audit-event', selectedId],
    queryFn: () => getAuditEvent(selectedId!),
    enabled: Boolean(selectedId),
  });
  const exportQuery = useQuery({
    queryKey: ['audit-export', exportId],
    queryFn: () => getAuditExport(exportId!),
    enabled: Boolean(exportId),
    refetchInterval: (query) =>
      ['queued', 'processing'].includes(query.state.data?.status ?? '') ? 1500 : false,
  });
  const exportMutation = useMutation({
    mutationFn: () => createAuditExport(filters),
    onSuccess: (result) => {
      setExportId(result.id);
      notify(t('auditExportQueued'), 'success');
    },
    onError: (error) => notify(error.message, 'error'),
  });
  const setFilter = (key: keyof AuditFilters, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
    setSelectedId(null);
  };
  const activeFilter = Object.values(filters).some(Boolean);

  return (
    <PageShell title={t('auditConsole')} description={t('auditConsoleDescription')}>
      <section className="grid gap-3 border-y py-4" aria-label={t('auditFilters')}>
        <h2 className="flex items-center gap-2 text-base"><Filter className="h-4 w-4" aria-hidden="true" />{t('filters')}</h2>
        <div className="grid gap-3 md:grid-cols-[minmax(14rem,1fr)_12rem_12rem_auto]">
          <div className="grid gap-1.5">
            <Label htmlFor="audit-search">{t('search')}</Label>
            <Input id="audit-search" value={filters.q} onChange={(event) => setFilter('q', event.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label>{t('category')}</Label>
            <Select value={filters.category || 'all'} onValueChange={(value) => setFilter('category', value === 'all' ? '' : value)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('all')}</SelectItem>
                <SelectItem value="account_security">{t('accountSecurity')}</SelectItem>
                <SelectItem value="project_governance">{t('projectGovernance')}</SelectItem>
                <SelectItem value="submission_review">{t('submissionReview')}</SelectItem>
                <SelectItem value="audit_access">{t('auditAccess')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>{t('outcome')}</Label>
            <Select value={filters.outcome || 'all'} onValueChange={(value) => setFilter('outcome', value === 'all' ? '' : value)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('all')}</SelectItem>
                <SelectItem value="succeeded">{t('succeeded')}</SelectItem>
                <SelectItem value="denied">{t('denied')}</SelectItem>
                <SelectItem value="failed">{t('failed')}</SelectItem>
                <SelectItem value="queued">{t('queued')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button className="self-end" type="button" variant="outline" onClick={() => exportMutation.mutate()} disabled={!activeFilter || exportMutation.isPending}>
            <FileSearch className="h-4 w-4" aria-hidden="true" />
            {t('export')}
          </Button>
        </div>
      </section>

      {exportId ? (
        <section className="flex flex-wrap items-center gap-3 border-b pb-4" aria-label={t('auditExportStatus')}>
          <StatusBadge status={exportQuery.data?.status ?? 'queued'} />
          <span className="text-sm">{exportQuery.data?.exportedCount ?? 0} {t('rows')}</span>
          {exportQuery.data?.capabilities.canDownload ? (
            <Button type="button" size="sm" onClick={() => downloadAuditExport(exportId)}>
              <Download className="h-4 w-4" aria-hidden="true" />
              {t('downloadCsv')}
            </Button>
          ) : null}
          {exportQuery.data?.status === 'failed' ? (
            <Button type="button" size="sm" variant="outline" onClick={() => exportMutation.mutate()}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t('retry')}
            </Button>
          ) : null}
        </section>
      ) : null}

      <div className="grid min-h-[32rem] min-w-0 gap-4 lg:grid-cols-[minmax(20rem,0.9fr)_minmax(22rem,1.1fr)]">
        <section className="panel grid min-h-0 grid-rows-[auto_1fr]" aria-label={t('auditEventList')}>
          <div className="flex items-center justify-between gap-2">
            <h2>{t('events')}</h2>
            <span className="text-sm text-muted-foreground">{events.length} {t('loaded')}</span>
          </div>
          {eventsQuery.isLoading ? <DataState state="loading" message={t('loadingAuditEvents')} /> : events.length ? (
            <ul className="mt-3 max-h-[34rem] divide-y overflow-y-auto">
              {events.map((event) => (
                <li key={event.id}>
                  <Button type="button" variant="ghost" className="h-auto w-full justify-start rounded-none px-1 py-3 text-left" onClick={() => setSelectedId(event.id)}>
                    <span className="grid min-w-0 gap-1">
                      <strong className="truncate">{event.summary}</strong>
                      <span className="flex flex-wrap gap-2 text-xs text-muted-foreground"><span>{event.category}</span><span>{event.outcome}</span></span>
                    </span>
                  </Button>
                </li>
              ))}
            </ul>
          ) : <DataState state="empty" title={activeFilter ? t('noMatchingEvents') : t('noAuditEvents')} message={t('adjustAuditFilters')} />}
        </section>
        {selectedId ? <AuditEventDetail event={detailQuery.data} onClose={() => setSelectedId(null)} /> : <AuditEventDetail />}
      </div>
    </PageShell>
  );
}
