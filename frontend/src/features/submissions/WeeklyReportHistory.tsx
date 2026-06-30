import type { WeeklyReport } from './api';

export function WeeklyReportHistory({ reports = [] }: { reports?: WeeklyReport[] }) {
  return (
    <section className="panel" aria-labelledby="weekly-report-history-heading">
      <h2 id="weekly-report-history-heading">Report history</h2>
      {reports.length === 0 ? <p className="muted">No weekly reports submitted yet.</p> : null}
      <ol className="timeline">
        {reports.map((report) => (
          <li key={report.id}>
            <strong>Week {report.report_week_start}</strong>
            <span>{report.review_status}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
