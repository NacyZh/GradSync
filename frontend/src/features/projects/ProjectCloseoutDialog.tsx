import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, CircleAlert, PackageCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { translateUiText } from '@/shared/i18n/translate';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { DataState } from '@/shared/ui/DataState';
import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/primitives/dialog';
import { Textarea } from '@/shared/ui/primitives/textarea';

import { useAppFeedback } from '../../shared/ui/AppFeedback';
import {
  completeProjectCloseout,
  getProjectCloseout,
  type ProjectCloseoutCheck,
} from './api';

const checkLabels: Record<ProjectCloseoutCheck['key'], string> = {
  incompleteTasks: 'Incomplete tasks',
  pendingReports: 'Reports awaiting review or revision',
  pendingMaterialPermissions: 'Materials awaiting visibility classification',
  unacceptedRequiredDeliverables: 'Required deliverables not accepted',
  unreturnedResources: 'Resources in use or not returned',
  openBookings: 'Pending or future resource bookings',
};

const checkPaths: Partial<Record<ProjectCloseoutCheck['key'], (projectId: number) => string>> = {
  pendingMaterialPermissions: (projectId) => `/projects/${projectId}/materials`,
  unacceptedRequiredDeliverables: (projectId) => `/projects/${projectId}/execution`,
  unreturnedResources: (projectId) => `/projects/${projectId}/resources`,
  openBookings: (projectId) => `/projects/${projectId}/resources`,
};

export function ProjectCloseoutDialog({
  projectId,
  open,
  onOpenChange,
  onArchived,
}: {
  projectId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onArchived: () => void | Promise<void>;
}) {
  const { locale } = useI18n();
  const tr = (value: string) => translateUiText(value, locale);
  const { notify } = useAppFeedback();
  const [cancelTasks, setCancelTasks] = useState(false);
  const [closeReports, setCloseReports] = useState(false);
  const [cancelBookings, setCancelBookings] = useState(false);
  const [materialsReviewed, setMaterialsReviewed] = useState(false);
  const [packageConfirmed, setPackageConfirmed] = useState(false);
  const [notes, setNotes] = useState('');
  const preflight = useQuery({
    queryKey: ['project-closeout', projectId],
    queryFn: () => getProjectCloseout(projectId),
    enabled: open,
  });
  const checks = preflight.data?.checks ?? [];
  const checkByKey = new Map(checks.map((check) => [check.key, check]));

  useEffect(() => {
    if (!open) return;
    setCancelTasks(false);
    setCloseReports(false);
    setCancelBookings(false);
    setMaterialsReviewed(false);
    setPackageConfirmed(false);
    setNotes('');
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => completeProjectCloseout(projectId, {
      cancelOpenTasks: cancelTasks,
      closePendingReports: closeReports,
      cancelOpenBookings: cancelBookings,
      materialsReviewed,
      finalPackageConfirmed: packageConfirmed,
      notes,
    }),
    onSuccess: async () => {
      notify(tr('Project closeout completed'), 'success');
      onOpenChange(false);
      await onArchived();
    },
    onError: (error) => notify(error.message, 'error'),
  });

  const hardBlocked = checks.some((check) => check.severity === 'blocked' && check.count > 0);
  const unresolvedDisposition = Boolean(
    (checkByKey.get('incompleteTasks')?.count && !cancelTasks)
    || (checkByKey.get('pendingReports')?.count && !closeReports)
    || (checkByKey.get('openBookings')?.count && !cancelBookings)
  );
  const canArchive = !hardBlocked
    && !unresolvedDisposition
    && materialsReviewed
    && packageConfirmed
    && !mutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100vh-2rem)] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{tr('Archive project?')}</DialogTitle>
          <DialogDescription>
            {tr('Complete the closeout checklist before the project becomes read-only.')}
          </DialogDescription>
        </DialogHeader>

        {preflight.isLoading ? <DataState state="loading" message={tr('Checking project closeout readiness.')} /> : null}
        {preflight.isError ? (
          <DataState
            state="error"
            title={tr('Closeout check unavailable')}
            message={preflight.error.message}
            action={<Button variant="outline" onClick={() => preflight.refetch()}>{tr('Retry')}</Button>}
          />
        ) : null}

        {preflight.data ? (
          <>
            <section className="grid gap-2" aria-label={tr('Project closeout checklist')}>
              {checks.map((check) => {
                const Icon = check.severity === 'blocked'
                  ? AlertTriangle
                  : check.severity === 'attention'
                    ? CircleAlert
                    : CheckCircle2;
                const path = checkPaths[check.key]?.(projectId);
                return (
                  <article className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-md border p-3" key={check.key}>
                    <Icon className={`h-4 w-4 ${check.severity === 'blocked' ? 'text-destructive' : check.severity === 'attention' ? 'text-amber-600' : 'text-emerald-600'}`} />
                    <div className="min-w-0">
                      <strong className="block text-sm">{tr(checkLabels[check.key])}</strong>
                      <span className="text-xs text-muted-foreground">{check.count} {tr('items')}</span>
                    </div>
                    {path && check.count ? <Link className="text-xs font-bold text-primary" to={path}>{tr('Resolve')}</Link> : <Badge variant={check.count ? 'warning' : 'success'}>{tr(check.severity)}</Badge>}
                  </article>
                );
              })}
            </section>

            {hardBlocked ? (
              <DataState
                state="warning"
                title={tr('Closeout is blocked')}
                message={tr('Return active resources, accept required deliverables, and resolve material classification before archiving.')}
              />
            ) : null}

            <section className="grid gap-3" aria-label={tr('Closeout dispositions')}>
              {checkByKey.get('incompleteTasks')?.count ? (
                <CloseoutChoice checked={cancelTasks} onChange={setCancelTasks} label={tr('Cancel all remaining tasks')} />
              ) : null}
              {checkByKey.get('pendingReports')?.count ? (
                <CloseoutChoice checked={closeReports} onChange={setCloseReports} label={tr('Close pending reports as unresolved')} />
              ) : null}
              {checkByKey.get('openBookings')?.count ? (
                <CloseoutChoice checked={cancelBookings} onChange={setCancelBookings} label={tr('Cancel pending and future bookings')} />
              ) : null}
              <CloseoutChoice checked={materialsReviewed} onChange={setMaterialsReviewed} label={tr('I reviewed final material visibility and access')} />
              <CloseoutChoice checked={packageConfirmed} onChange={setPackageConfirmed} label={tr('Accepted deliverables and evidence form the final outcomes package')} />
              <label className="grid gap-1.5 text-sm font-bold">
                {tr('Closeout notes')}
                <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={4000} placeholder={tr('Record handover or retention notes')} />
              </label>
            </section>
          </>
        ) : null}

        <DialogFooter>
          <Button variant="outline" type="button" onClick={() => onOpenChange(false)}>{tr('Cancel')}</Button>
          <Button variant="destructive" type="button" disabled={!canArchive} onClick={() => mutation.mutate()}>
            <PackageCheck className="h-4 w-4" />
            {tr('Complete closeout and archive')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CloseoutChoice({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex items-start gap-3 rounded-md border p-3 text-sm font-bold">
      <input className="mt-0.5 h-4 w-4 accent-primary" type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}
