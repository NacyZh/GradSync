# Production Infrastructure

GradSync production is a Docker Compose deployment with one public frontend
entry point, an internal backend API, PostgreSQL, Redis, Celery worker, and
Celery scheduler.

## Host Profile

| Area | Minimum Viable Single-Node Host | Recommended Production Host | Acceptance Check |
|------|----------------------------------|-----------------------------|------------------|
| CPU | 2 vCPU with low-memory deploy mode | 4 dedicated vCPU | Dashboard and search performance tests pass at seeded scale |
| Memory | 1 GB RAM with `COMPOSE_PARALLEL_LIMIT=1`, one Gunicorn worker, one Celery worker process, and serial image builds | 8 GB RAM | No service OOM events during deploy and one reminder cycle |
| Disk | 40 GB SSD for app and database volumes | 100 GB SSD for app and database volumes | PostgreSQL volume has 30 days projected headroom |
| Network | Public 80/443 to TLS terminator, SSH restricted to operators | Same | Firewall review is attached to release ticket |
| OS | Supported Linux distribution with Docker Engine and Compose plugin | Same | `docker compose version` recorded in release notes |
| Time | NTP synchronized | Same | TLS, audit, and notification timestamps are monotonic |

The 2 vCPU/1 GB profile is capacity-constrained. Deploy through
`scripts/deploy-production.sh`, keep the default low-memory runtime settings in
`.env.production`, and do not run manual `docker compose up --build` deploys.
Do not flush Linux page cache during deployment; release Docker build state with
builder/image pruning instead.

## Service Placement

- `frontend` is the only service exposed publicly.
- `backend`, `worker`, `scheduler`, `db`, and `redis` run on internal Compose
  networks only.
- PostgreSQL and Redis use named persistent volumes.
- Backups are written locally first and copied to encrypted off-host storage.
- Operators access the host through the deploy user with least-privilege SSH.

## Acceptance Checklist

- DNS resolves the production domain to the TLS terminator.
- Firewall exposes only 80/443 publicly and restricts SSH.
- `docker-compose.prod.yml` starts all services with healthy backend, frontend,
  database, and Redis checks.
- `python manage.py migrate --check` has no unapplied migrations after deploy.
- `worker` and `scheduler` run for at least one reminder cycle without queue
  buildup.
- Off-host backup copy succeeds and restore drill evidence is current.
