# GradSync

GradSync manages graduate research group operations across project-scoped tasks,
draft reviews, weekly progress reports, lab resource bookings, and notification
records.

## Stack

- Backend: Django, Django REST Framework, Celery
- Frontend: React, TypeScript, Vite
- Persistence: PostgreSQL
- Background jobs/cache: Redis
- Orchestration: Docker Compose

## Local Setup

```bash
cp .env.example .env
docker compose up --build
```

The local backend container runs migrations and seeds demo accounts on startup.
To refresh the seeded demo data manually, run:

```bash
docker compose exec backend python manage.py seed_demo_research_ops
```

Seeded demo accounts:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@gradsync.local` | `admin123` |
| Advisor | `advisor@example.com` | `advisor123` |
| Student | `student@example.com` | `student123` |
| Reviewer | `reviewer@example.com` | `reviewer123` |

## Validation

## Development Governance

GradSync follows Spec-Kit SDD. Business changes must update `specs/` first,
then plan/design artifacts, then test-first implementation tasks. The governing
rules are in `.specify/memory/constitution.md`.

Every feature PR should include the relevant `spec.md`, `plan.md`,
`research.md`, `data-model.md`, contracts, tasks, code, and tests. Business
code without a matching specification change is not releasable.

## Validation

```bash
docker compose exec backend pytest
docker compose exec frontend npm test
docker compose exec frontend npm run test:e2e
```

Frontend release checks include Tailwind/shadcn component coverage, role-aware
workspace navigation tests, full-stack Playwright workflow tests, and production
layout screenshot checks:

```bash
cd frontend
npm run lint
npm test
GRADSYNC_E2E_MODE=fullstack npm run test:e2e
npm run test:e2e -- production-ui.spec.ts
npm run test:e2e -- research-assets-locale.spec.ts
npm run build
```

Run `sh scripts/check-generated-artifacts.sh` from the repository root before
reviewing a branch. Playwright screenshots and traces are written to `/tmp` by
the test config and must not be committed.

US4 research asset validation is covered by backend paper/code/locale contract
and unit tests, `frontend/tests/component/research-assets-locale.test.tsx`, and
`frontend/tests/e2e/research-assets-locale.spec.ts`.

See `specs/001-research-group-ops/quickstart.md` for scenario validation.

## Production Deployment

Production runs from immutable backend and frontend images:

```bash
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml up --build
```

The production topology runs Gunicorn for Django, nginx for static frontend
assets and API proxying, internal-only PostgreSQL/Redis networks, container
healthchecks, a one-shot migration service, Celery worker/scheduler services,
and persistent PostgreSQL/Redis volumes. Run readiness checks before release:

```bash
docker compose -f docker-compose.prod.yml run --rm backend python manage.py check --deploy
docker compose -f docker-compose.prod.yml run --rm backend python manage.py check_production_readiness --repo-root /app
```

Operational runbooks for rollout, rollback, backups, incident response, secret
rotation, and vulnerability remediation are in `docs/production.md`.
