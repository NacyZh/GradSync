import { CalendarDays } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/primitives/card';
import { DataState } from '../../shared/ui/DataState';
import { StatusBadge } from '../../shared/ui/StatusBadge';
import type { WeeklyReport } from './api';

export function WeeklyReportHistory({ reports = [] }: { reports?: WeeklyReport[] }) {
  return (
    <section aria-labelledby="weekly-report-history-heading">
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle id="weekly-report-history-heading" className="flex items-center gap-2 text-base">
            <CalendarDays className="h-4 w-4" aria-hidden="true" />
            Report history
          </CardTitle>
          <CardDescription>Submitted weekly updates and review state.</CardDescription>
        </CardHeader>
        <CardContent>
          {reports.length === 0 ? <DataState state="empty" title="No reports" message="No weekly reports submitted yet." /> : null}
          <ol className="timeline">
            {reports.map((report) => (
              <li key={report.id}>
                <div>
                  <strong>
                    Week {report.report_week_start}
                    {report.revision_number && report.revision_number > 1 ? ` · Revision ${report.revision_number}` : ''}
                  </strong>
                  <p className="text-sm text-muted-foreground">{report.completed_work}</p>
                  {report.blockers ? <p className="text-sm text-muted-foreground">Blockers: {report.blockers}</p> : null}
                </div>
                <StatusBadge status={report.review_status} />
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </section>
  );
}
