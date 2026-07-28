# Monitoring And Alerts

GradSync exposes `/healthz`, `/readyz`, `/metrics`, structured request logs, and
error reporting hooks. Production launch requires alert routing, not just metric
collection.

## Alert Routes

| Signal | Threshold | Target | Validation |
|--------|-----------|--------|------------|
| Frontend healthcheck failure | 2 consecutive failures | Primary on-call | Stop frontend container in staging |
| Backend readiness failure | 2 consecutive failures | Primary on-call | Block database or Redis in staging |
| HTTP 5xx rate | More than 1% for 5 minutes | Primary on-call | Synthetic 500 test route or log replay |
| P95 request latency | Above 2 seconds for 10 minutes | Primary on-call | Load test seeded project dashboard |
| Notification backlog | Pending notifications older than 5 minutes | Operations owner | Pause worker in staging |
| Notification delivery failures | 5 failures in 10 minutes | Operations owner | Invalid SMTP credential in staging |
| Worker absent | No worker heartbeat for 2 minutes | Primary on-call | Stop worker in staging |
| Scheduler absent | No scheduler heartbeat for 5 minutes | Primary on-call | Stop scheduler in staging |
| Error reporting event spike | 5 application exceptions in 5 minutes | Application owner | Trigger handled exception in staging |
| Backup job failure | Any scheduled failure | Database owner | Force failed backup target in staging |
| Recovery throttle spike | More than 25 rejected requests in 10 minutes | Security owner | Controlled recovery-rate probe |
| Security email retry backlog | Any recovery/email-change notice older than 10 minutes | Operations owner | Disable SMTP in staging |
| Session revocation failure | Any failed authoritative revocation | Security owner | Revoke a seeded secondary session |
| Required audit write failure | Any occurrence | Primary on-call | Simulate audit database write failure |
| Project governance hold | Any unresolved project | Governance owner | Mark a staging owner ineligible |
| Primary advisor conflict | Any project with multiple active primary roles | Security owner | Run migration conflict fixture |
| Audit export queue age | Oldest queued/processing export over 5 minutes | Operations owner | Pause Celery worker in staging |
| Audit export failure | Any failed export | Application owner | Force storage write failure in staging |
| Reporting period generation lag | No open period for an active scheduled project | Application owner | Disable Beat period maintenance in staging |
| Structured report backfill lag | Any unlinked legacy report after rollout | Application owner | Run migration against a restored fixture |
| Actionable high/overdue risk | Any unresolved high or overdue record past escalation delay | Project governance owner | Seed a past-due high risk |
| Report analytics failure | 5 failed bounded requests in 10 minutes | Application owner | Disable Redis and verify source fallback |

## Required Configuration

- `ALERT_WEBHOOK_URL` points to the alert manager or incident tool.
- `ALERT_ONCALL_TARGET` identifies the production escalation target.
- `SENTRY_DSN` is set when error reporting is required by the release.
- Alert dry-run evidence is attached to the release ticket.

## Account Security Signals

- `gradsync_account_recovery_pending` counts current recovery records without
  exposing email addresses, IP values, or recovery tokens.
- `gradsync_account_sessions_revoked` confirms authoritative revocation
  activity. A revoked `sid` must fail on the next protected request.
- Correlate account-security audit events and delivery failures using
  `X-Request-ID`; never log reset links, verification codes, cookies, bearer
  tokens, password values, or raw request bodies.
- Recovery acknowledgement remains generic during SMTP or audit degradation.
  Alert on the dependency failure rather than returning account-specific
  delivery state to the public requester.

## Project Governance Signals

- Production readiness reports held projects as bounded `project_id:reason`
  pairs. It must not include member names, addresses, assignment notes, or
  submission content.
- Any project with zero eligible primary advisors enters governance hold.
  Multiple active primary memberships are a data-integrity incident and block
  readiness.
- Correlate collaborator assignment, role removal, ownership transfer, hold,
  hold resolution, and review assignment events by request ID. A removed role
  or assignment must be denied on the next request.

## Audit Export Signals

- `gradsync_audit_exports_pending` and
  `gradsync_audit_export_queue_age_seconds` show worker backlog without exposing
  filters or exported rows.
- `gradsync_audit_exports_failed` identifies safe retry demand. Ordinary
  project and account reads remain available while export generation is
  degraded.
- Ready CSV files expire according to `GRADSYNC_AUDIT_EXPORT_TTL_SECONDS`.
  Cleanup removes the file while preserving immutable event and export
  evidence.

## Research Execution Signals

- `gradsync_reporting_periods_open` confirms active reporting windows.
- `gradsync_structured_reports_unlinked` must reach zero after backfill.
- `gradsync_risks_actionable` counts high or overdue active risks without
  exposing titles, descriptions, owners, rationale, or linked labels.
- Beat registers reporting-period maintenance, risk-review reminders, and
  actionable notification follow-ups idempotently.
- Redis failure may increase analytics latency but must not block source reads.
