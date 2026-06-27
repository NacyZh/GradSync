# Production Infrastructure

GradSync production is a Docker Compose deployment with one public frontend
entry point, an internal backend API, PostgreSQL, Redis, Celery worker, and
Celery scheduler.

## Minimum Host Profile

| Area | Requirement | Acceptance Check |
|------|-------------|------------------|
| CPU | 4 dedicated vCPU | Dashboard and search performance tests pass at seeded scale |
| Memory | 8 GB RAM minimum | No service OOM events during one reminder cycle |
| Disk | 100 GB SSD for app and database volumes | PostgreSQL volume has 30 days projected headroom |
| Network | Public 80/443 to TLS terminator, SSH restricted to operators | Firewall review is attached to release ticket |
| OS | Supported Linux distribution with Docker Engine and Compose plugin | `docker compose version` recorded in release notes |
| Time | NTP synchronized | TLS, audit, and notification timestamps are monotonic |

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
