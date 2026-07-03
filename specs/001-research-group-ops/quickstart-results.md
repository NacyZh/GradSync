# Quickstart Validation Results: Research Group Operations

**Date**: 2026-07-02

## Summary

Result: PASS

The Docker Compose quickstart was executed with backend, frontend, PostgreSQL,
Redis, worker, scheduler, and Mailpit services. Migrations and validation seed
data completed successfully. Backend, frontend component, and Playwright e2e
checks passed in containers.

## Commands Run

| Command | Result | Notes |
|---------|--------|-------|
| `docker compose up --build -d` | PASS | Built and started the full stack. |
| `docker compose exec backend python manage.py migrate` | PASS | Applied app, Django, Celery Beat, and Celery Results migrations. |
| `docker compose exec backend python manage.py seed_validation_research_ops` | PASS | Seeded `advisor@example.com` and `student@example.com`. |
| `docker compose restart scheduler` | PASS | Required after migrations because the initial scheduler start happened before Celery Beat tables existed. |
| `docker compose exec backend pytest` | PASS | 28 passed, 5 warnings. |
| `docker compose exec frontend npm test` | PASS | 3 files passed, 6 tests passed. |
| `docker compose exec frontend npm run test:e2e` | PASS | 5 Playwright Chromium tests passed. |
| `docker compose ps -a` | PASS | Backend, frontend, database, Redis, worker, scheduler, and Mailpit were running. |
| `../.venv/bin/python -m pytest tests/contract/test_papers_api.py tests/contract/test_code_artifacts_api.py tests/contract/test_locale_api.py tests/unit/test_paper_duplicate_rules.py tests/unit/test_asset_upload_policy.py tests/unit/test_code_artifact_rules.py tests/integration/test_research_assets_project_scope.py` | PASS | 11 US4 backend contract/unit/integration tests passed. |
| `../.venv/bin/python -m pytest tests/integration/test_research_asset_performance.py tests/integration/test_research_assets_project_scope.py` | PASS | Research asset search and duplicate detection performance checks passed. |
| `npm test -- --run tests/component/research-assets-locale.test.tsx` | PASS | 4 component tests passed for paper/code/locale UI states. |
| `npm run test:e2e -- research-assets-locale.spec.ts` | PASS | Focused paper import, code download, and locale workflow passed in Playwright mock mode. |
| `npm run lint && npm run build` | PASS | Frontend lint and production build passed with US4 route chunks. |
| `sh scripts/check-generated-artifacts.sh` | PASS | Generated artifact guard passed after cleaning local runtime/build artifacts. |
| `PYTHON=.venv/bin/python bash scripts/check-openapi-contract.sh` | PASS | 28 contract operations covered by generated schema. |
| `../.venv/bin/python -m pytest tests/contract/test_papers_api.py tests/contract/test_code_artifacts_api.py tests/contract/test_locale_api.py tests/contract/test_resources_bookings_api.py tests/unit/test_asset_upload_policy.py tests/unit/test_code_artifact_rules.py tests/unit/test_paper_duplicate_rules.py tests/unit/test_booking_rules.py tests/integration/test_research_assets_project_scope.py tests/integration/test_booking_conflicts.py tests/integration/test_booking_project_scope.py tests/integration/test_convergence_workflows.py tests/integration/test_production_readiness.py` | PASS | 37 updated convergence backend tests passed for configurable resources, local imports, email delivery status, and production readiness. |
| `npm test -- --run tests/component/login.test.tsx tests/component/research-assets-locale.test.tsx tests/component/resource-booking.test.tsx tests/component/role-navigation.test.tsx` | PASS | 22 component tests passed for production login, locale-aware assets, resources, and workspace navigation. |
| `npm run test:e2e -- auth-login.spec.ts resource-booking.spec.ts research-assets-locale.spec.ts` | PASS | 7 Playwright Chromium tests passed for login, resource booking, paper/code assets, and locale workflow reachability. |

## Validation Notes

- The scheduler initially exited with `relation "django_celery_beat_crontabschedule" does not exist` because Compose started it before the first database migration. Running migrations and restarting the scheduler resolved the issue; the scheduler remained up afterward.
- Playwright initially discovered Vitest component tests because no dedicated Playwright configuration existed. `frontend/playwright.config.ts` now restricts e2e discovery to `tests/e2e`.
- The frontend Docker image initially lacked Playwright browser binaries. `docker/frontend.Dockerfile` now installs Chromium and its dependencies so `docker compose exec frontend npm run test:e2e` is reproducible.
- E2e tests initially used an ambiguous `GradSync` text locator. They now target the unique page heading.
- US4 validation added paper duplicate handling, code artifact version conflict,
  authorized download audit, account locale persistence, focused component
  tests, and a Playwright workflow for paper/code/locale routes.
- 2026-07-02 convergence validation replaced fixed lab resources with
  configurable resource types/items, replaced production-facing demo seeding with
  validation seeding, verified local paper/code import semantics, confirmed
  immediate locale provider updates, checked centered production login behavior,
  and added an explicit email delivery membership re-check test.

## Residual Risks

- Docker image build output reported 5 npm audit vulnerabilities from installed frontend dependencies. These were not remediated during quickstart validation because the quickstart task was scoped to build/test validation and `npm audit fix --force` may introduce breaking dependency changes.
- Full-stack Playwright coverage for the new US4 route currently depends on the
  broader seeded e2e environment; the focused US4 Playwright flow passed in mock
  mode, while backend contract/integration tests validate the real Django API.
