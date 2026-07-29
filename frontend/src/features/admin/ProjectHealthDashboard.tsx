import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  BellRing,
  CirclePause,
  FileClock,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatUiDate, translateUiText } from '@/shared/i18n/translate';
import { DataState } from '@/shared/ui/DataState';
import { Badge } from '@/shared/ui/primitives/badge';
import { Button } from '@/shared/ui/primitives/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/shared/ui/primitives/tooltip';

import { getProjectHealthSnapshot, type ProjectHealthRow } from './api';

type Props = {
  compact?: boolean;
};

export function ProjectHealthDashboard({ compact = false }: Props) {
  const { locale } = useI18n();
  const tr = (value: string) => translateUiText(value, locale);
  const query = useQuery({
    queryKey: ['admin-project-health'],
    queryFn: getProjectHealthSnapshot,
    refetchInterval: 60_000,
  });
  const snapshot = query.data;

  if (query.isLoading) {
    return <DataState state="loading" message={tr('Loading cross-project health.')} />;
  }
  if (query.error || !snapshot) {
    return (
      <DataState
        state="error"
        title={tr('Project health unavailable')}
        message={query.error?.message ?? tr('The operations snapshot could not be loaded.')}
        action={<Button variant="outline" onClick={() => query.refetch()}>{tr('Retry')}</Button>}
      />
    );
  }

  const metrics = [
    {
      label: tr('Overdue project rate'),
      value: `${snapshot.summary.overdueProjectRate}%`,
      detail: `${snapshot.summary.overdueProjects}/${snapshot.summary.activeProjects} ${tr('active projects')}`,
      icon: AlertTriangle,
      tone: snapshot.summary.overdueProjects ? 'text-destructive' : 'text-emerald-600',
    },
    {
      label: tr('Long-term blocked tasks'),
      value: snapshot.summary.longBlockedTasks,
      detail: `${snapshot.longBlockedDays}+ ${tr('days blocked')}`,
      icon: CirclePause,
      tone: snapshot.summary.longBlockedTasks ? 'text-amber-600' : 'text-emerald-600',
    },
    {
      label: tr('Missing reports'),
      value: snapshot.summary.missingReports,
      detail: `${snapshot.windowDays} ${tr('day window')}`,
      icon: FileClock,
      tone: snapshot.summary.missingReports ? 'text-amber-600' : 'text-emerald-600',
    },
    {
      label: tr('Governance holds'),
      value: snapshot.summary.governanceHolds,
      detail: tr('Projects frozen for intervention'),
      icon: ShieldAlert,
      tone: snapshot.summary.governanceHolds ? 'text-destructive' : 'text-emerald-600',
    },
    {
      label: tr('Resource conflicts'),
      value: snapshot.summary.resourceConflicts,
      detail: `${snapshot.windowDays} ${tr('day window')}`,
      icon: AlertTriangle,
      tone: snapshot.summary.resourceConflicts ? 'text-amber-600' : 'text-emerald-600',
    },
    {
      label: tr('Notification failures'),
      value: snapshot.summary.notificationFailures,
      detail: `${snapshot.summary.notificationFailureRate}% ${tr('failure rate')}`,
      icon: BellRing,
      tone: snapshot.summary.notificationFailures ? 'text-destructive' : 'text-emerald-600',
    },
  ];

  return (
    <section className="space-y-4" aria-label={tr('Cross-project health')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2>{tr('Cross-project health')}</h2>
          <p className="text-sm text-muted-foreground">
            {tr('Operational risks across active research projects.')} {tr('Updated')} {formatUiDate(snapshot.generatedAt, { dateStyle: 'medium', timeStyle: 'short' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {compact ? <Link className="inline-action font-bold text-primary" to="/admin/health">{tr('Open health console')}</Link> : null}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="icon" variant="outline" onClick={() => query.refetch()} disabled={query.isFetching} aria-label={tr('Refresh health snapshot')}>
                <RefreshCw className={`h-4 w-4 ${query.isFetching ? 'animate-spin' : ''}`} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{tr('Refresh health snapshot')}</TooltipContent>
          </Tooltip>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {metrics.map(({ label, value, detail, icon: Icon, tone }) => (
          <article className="rounded-md border bg-card p-4" key={label}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-xs font-bold uppercase text-muted-foreground">{label}</span>
              <Icon className={`h-4 w-4 shrink-0 ${tone}`} aria-hidden="true" />
            </div>
            <strong className="mt-3 block text-2xl">{value}</strong>
            <span className="mt-1 block text-xs text-muted-foreground">{detail}</span>
          </article>
        ))}
      </div>

      {compact ? (
        <ProjectRiskTable projects={snapshot.projects.slice(0, 5)} tr={tr} compact />
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-[minmax(26rem,1.35fr)_minmax(20rem,0.65fr)]">
            <ProjectRiskTable projects={snapshot.projects} tr={tr} />
            <OperationsTrend trend={snapshot.trend} tr={tr} />
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <OperationsQueue
              title={tr('Long-term blockers')}
              empty={tr('No tasks have remained blocked past the threshold.')}
              rows={snapshot.blockedTasks.map((task) => ({
                id: `task-${task.taskId}`,
                title: task.title,
                detail: `${task.projectTitle} · ${task.blockedDays} ${tr('days blocked')}`,
                path: task.actionPath,
              }))}
            />
            <OperationsQueue
              title={tr('Missing report queue')}
              empty={tr('No overdue reporting slots are missing submissions.')}
              rows={snapshot.missingReports.map((report) => ({
                id: `report-${report.periodId}-${report.projectId}`,
                title: report.projectTitle,
                detail: `${formatUiDate(report.periodStart)} · ${report.missingCount} ${tr('missing submissions')}`,
                path: report.actionPath,
              }))}
            />
            <OperationsQueue
              title={tr('Governance intervention')}
              empty={tr('No active project is under a governance hold.')}
              rows={snapshot.governanceHolds.map((hold) => ({
                id: `hold-${hold.projectId}`,
                title: hold.projectTitle,
                detail: tr(hold.reason.replaceAll('_', ' ')),
                path: hold.actionPath,
              }))}
            />
          </div>
        </>
      )}
    </section>
  );
}

function ProjectRiskTable({
  projects,
  tr,
  compact = false,
}: {
  projects: ProjectHealthRow[];
  tr: (value: string) => string;
  compact?: boolean;
}) {
  return (
    <section className="panel min-w-0" aria-label={tr('Project risk ranking')}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3>{tr('Project risk ranking')}</h3>
          <p className="text-sm text-muted-foreground">{tr('Lowest health score appears first.')}</p>
        </div>
        <Badge variant="secondary">{projects.length}</Badge>
      </div>
      {projects.length === 0 ? <DataState state="empty" title={tr('No active projects')} message={tr('Active projects will appear here.')} /> : (
        <div className={`overflow-auto ${compact ? 'max-h-72' : 'max-h-[34rem]'}`}>
          <table className="w-full min-w-[52rem] border-collapse text-sm">
            <thead className="sticky top-0 bg-card text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-2 py-2">{tr('Project')}</th>
                <th className="px-2 py-2">{tr('Health')}</th>
                <th className="px-2 py-2">{tr('Overdue tasks')}</th>
                <th className="px-2 py-2">{tr('Blocked')}</th>
                <th className="px-2 py-2">{tr('Missing reports')}</th>
                <th className="px-2 py-2">{tr('Governance')}</th>
                <th className="px-2 py-2">{tr('Operations')}</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr className="border-t align-top" key={project.projectId}>
                  <td className="px-2 py-3">
                    <Link className="font-bold text-primary hover:underline" to={project.actionPath}>{project.title}</Link>
                    <span className="block text-xs text-muted-foreground">{project.advisorName}</span>
                  </td>
                  <td className="px-2 py-3"><HealthBadge project={project} tr={tr} /></td>
                  <td className="px-2 py-3">{project.overdueTaskCount}</td>
                  <td className="px-2 py-3">{project.longBlockedTaskCount}</td>
                  <td className="px-2 py-3">{project.missingReportCount}</td>
                  <td className="px-2 py-3">{project.governanceState === 'hold' ? <Badge variant="destructive">{tr('hold')}</Badge> : <span>{tr('normal')}</span>}</td>
                  <td className="px-2 py-3">{project.resourceConflictCount} {tr('conflicts')} · {project.notificationFailureCount} {tr('failed')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function HealthBadge({ project, tr }: { project: ProjectHealthRow; tr: (value: string) => string }) {
  const variant = project.healthLevel === 'critical' ? 'destructive' : project.healthLevel === 'attention' ? 'warning' : 'success';
  return <Badge variant={variant}>{project.healthScore} · {tr(project.healthLevel)}</Badge>;
}

function OperationsTrend({
  trend,
  tr,
}: {
  trend: Array<{ date: string; resourceConflicts: number; notificationFailures: number }>;
  tr: (value: string) => string;
}) {
  const maximum = Math.max(1, ...trend.flatMap((point) => [point.resourceConflicts, point.notificationFailures]));
  return (
    <section className="panel min-w-0" aria-label={tr('Operations failure trend')}>
      <h3>{tr('Operations failure trend')}</h3>
      <p className="text-sm text-muted-foreground">{tr('Daily resource conflicts and notification delivery failures.')}</p>
      <div className="mt-5 grid h-56 items-end gap-1 border-b" style={{ gridTemplateColumns: `repeat(${trend.length}, minmax(0, 1fr))` }} role="img" aria-label={tr('Fourteen-day operations failure chart')}>
        {trend.map((point) => (
          <div className="flex h-full min-w-0 items-end justify-center gap-0.5" key={point.date} title={`${formatUiDate(point.date)}: ${point.resourceConflicts} ${tr('conflicts')}, ${point.notificationFailures} ${tr('failures')}`}>
            <span className="w-2 bg-amber-500" style={{ height: point.resourceConflicts ? `${Math.max((point.resourceConflicts / maximum) * 100, 5)}%` : 0 }} />
            <span className="w-2 bg-destructive" style={{ height: point.notificationFailures ? `${Math.max((point.notificationFailures / maximum) * 100, 5)}%` : 0 }} />
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-2"><i className="h-2.5 w-2.5 bg-amber-500" />{tr('Resource conflicts')}</span>
        <span className="flex items-center gap-2"><i className="h-2.5 w-2.5 bg-destructive" />{tr('Notification failures')}</span>
      </div>
    </section>
  );
}

function OperationsQueue({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: Array<{ id: string; title: string; detail: string; path: string }>;
}) {
  return (
    <section className="panel min-h-0" aria-label={title}>
      <div className="mb-3 flex items-center justify-between gap-3"><h3>{title}</h3><Badge variant="secondary">{rows.length}</Badge></div>
      {rows.length === 0 ? <p className="text-sm text-muted-foreground">{empty}</p> : (
        <ul className="max-h-72 divide-y overflow-y-auto">
          {rows.map((row) => <li className="py-3" key={row.id}><Link className="font-bold text-primary hover:underline" to={row.path}>{row.title}</Link><p className="text-sm text-muted-foreground">{row.detail}</p></li>)}
        </ul>
      )}
    </section>
  );
}
