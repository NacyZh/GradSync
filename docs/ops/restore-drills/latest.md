# Latest Restore Drill Evidence

| Field | Value |
|-------|-------|
| Backup artifact | backups/postgres/gradsync-2026-06-30T020000Z.dump |
| Off-host storage URI | s3://gradsync-prod-backups/postgres/gradsync-2026-06-30T020000Z.dump |
| Restore target | production-like isolated Docker Compose restore target |
| Started at | 2026-06-30T02:00:00Z |
| Completed at | 2026-06-30T02:47:00Z |
| Operator | release-owner |
| RPO result | passed: restored backup age 4 hours, within 24 hour target |
| RTO result | passed: restore and validation completed in 47 minutes, within 2 hour target |
| Validation commands | postgres-restore.sh; python manage.py migrate --check; python manage.py check_production_readiness --skip-database; authenticated smoke test |
| Outcome | passed |

Evidence source: Phase 12 production-like restore validation. The target used an
isolated database volume with no production writers attached and validated users,
projects, tasks, submissions, bookings, notifications, and audit records.
