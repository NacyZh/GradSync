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

Pushes to `main` run the GitHub Actions CI/CD workflow. After backend and
frontend checks pass, the `deploy-production` job connects to the production
host over SSH and runs `scripts/deploy-production.sh`.

The production host must already have:

- The repository cloned at `GRADSYNC_DEPLOY_PATH` (default
  `/home/GradSync/GradSync`).
- A clean working tree that can accept `git pull --ff-only`.
- Docker Engine and the Docker Compose plugin installed.
- A valid `.env.production` file, either maintained on the host or synced from
  the `PRODUCTION_ENV_FILE` GitHub secret.
- Git credentials or a deploy key that allow the host to fetch the GitHub
  repository.

GitHub production environment configuration:

| Name | Type | Purpose |
|------|------|---------|
| `PRODUCTION_DEPLOY_SSH_KEY` | Secret | Private SSH key used by Actions to connect to the host |
| `PRODUCTION_ENV_FILE` | Secret | Optional full `.env.production` contents to sync before deploy |
| `GRADSYNC_PRODUCTION_HOST` | Variable | Production server host or IP |
| `GRADSYNC_PRODUCTION_USER` | Variable | SSH user, defaults to `deploy` |
| `GRADSYNC_PRODUCTION_SSH_PORT` | Variable | SSH port, defaults to `22` |
| `GRADSYNC_DEPLOY_PATH` | Variable | Repository path on the server |
| `GRADSYNC_PUBLIC_URL` | Variable | Public URL used for post-deploy checks |

The deploy script performs:

1. `git fetch` and `git pull --ff-only` on the server.
2. `docker compose -f docker-compose.prod.yml build backend frontend`.
3. Start PostgreSQL and Redis.
4. Run migrations.
5. Recreate backend, frontend, worker, and scheduler.
6. Wait for healthy services.
7. Run `python manage.py check --deploy`.
8. Probe `/`, `/healthz/`, `/readyz/`, and `/api/schema/`.
9. Watch backend logs, worker logs, queue depth, notification failures, and
   request latency for at least one reminder cycle.

## Host Nginx

The host reverse proxy terminates TLS and forwards all application traffic to
the frontend container on port `8080`. Do not proxy browser traffic directly to
backend port `8000`; that bypasses the React static frontend and makes `/`
return Django's 404.

```nginx
server {
    listen 80;
    server_name 120021123.xyz www.120021123.xyz;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;

    server_name 120021123.xyz www.120021123.xyz;

    ssl_certificate /etc/letsencrypt/live/120021123.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/120021123.xyz/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

Validate the deployed routing with trailing slashes on backend health endpoints:

```bash
curl -I https://120021123.xyz/
curl -I https://120021123.xyz/healthz/
curl -I https://120021123.xyz/readyz/
curl -I https://120021123.xyz/api/schema/
```

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
