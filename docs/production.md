# Production Operations

## Release Checklist

- Build backend and frontend images from the release commit.
- Run backend tests, frontend tests, frontend build, migration check, dependency
  audit, image scan, and `python manage.py check --deploy`.
- Copy `.env.production.example` to `.env.production` and replace every
  placeholder secret before starting the stack.
- Start with `docker compose -f docker-compose.prod.yml up --build`.
- Confirm `frontend`, `backend`, `worker`, `scheduler`, `db`, and `redis`
  report healthy or running.
- Confirm `/healthz`, `/readyz`, `/metrics`, one authenticated API request, and
  one SMTP notification delivery path.

## Deployment

1. Build and scan images in CI.
2. Back up PostgreSQL before applying a release.
3. Pull or build the approved images on the host.
4. Run `docker compose -f docker-compose.prod.yml up -d migrate`.
5. Run `docker compose -f docker-compose.prod.yml up -d`.
6. Watch backend logs, worker logs, queue depth, notification failures, and
   request latency for at least one reminder cycle.

## Rollback

1. Keep the previous image tags and `.env.production` available.
2. If the release has no irreversible migration, redeploy the previous image
   tags and restart the stack.
3. If a migration must be reverted, stop writers, restore the latest known-good
   backup, deploy the previous image tags, and run readiness checks.
4. Record the incident timeline and failed checks before retrying the release.

## Backup And Restore

Create backups with:

```bash
POSTGRES_USER=gradsync POSTGRES_DB=gradsync ./scripts/postgres-backup.sh
```

Restore a backup with:

```bash
POSTGRES_USER=gradsync POSTGRES_DB=gradsync ./scripts/postgres-restore.sh backups/postgres/gradsync-TIMESTAMP.dump
```

Use `POSTGRES_BACKUP_RETENTION_DAYS` to control local backup retention. Store
off-host encrypted copies according to the deployment environment's retention
policy.

## Secret Rotation

- Rotate `DJANGO_SECRET_KEY` only with a planned maintenance window because it
  invalidates signed sessions and tokens.
- Rotate `POSTGRES_PASSWORD`, `EMAIL_HOST_PASSWORD`, and provider API keys by
  updating the provider first, then `.env.production`, then restarting affected
  services.
- Never copy values from `.env.example` into production.
- After rotation, run `check_production_readiness`, sign in, and send a test
  notification.

## Incident Response

- Check `/readyz` to separate application, database, and Redis failures.
- Check `/metrics` for pending notification buildup.
- Inspect `X-Request-ID` in user reports and match it to structured logs.
- If email delivery fails, pause scheduler processing if needed, fix SMTP
  credentials or provider availability, then retry failed notifications from an
  audited management action.
- If the database is impaired, stop writers before restore.

## Vulnerability Remediation

- Treat high and critical dependency or image findings as release blockers.
- Patch dependencies in the smallest supported version range and rerun the full
  release gate.
- Rebuild images even when only base image CVEs changed.
- Document accepted residual risk with an owner and review date.

## Alerting Guidance

Alert on backend or frontend healthcheck failures, database readiness failures,
Redis readiness failures, worker absence, scheduler absence, pending
notifications above the expected reminder window, repeated notification delivery
failures, and elevated 5xx responses grouped by request ID.
