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

## Required Configuration

- `ALERT_WEBHOOK_URL` points to the alert manager or incident tool.
- `ALERT_ONCALL_TARGET` identifies the production escalation target.
- `SENTRY_DSN` is set when error reporting is required by the release.
- Alert dry-run evidence is attached to the release ticket.
