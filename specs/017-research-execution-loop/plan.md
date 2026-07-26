# Implementation Plan: Research Execution Loop

**Branch**: `spec/feature-017` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-research-execution-loop/spec.md`

## Summary

Complete the research execution lifecycle across the existing Projects,
Submissions, Notifications, Schedules, Audit, and frontend feature boundaries.
The backend adds relational milestone, deliverable, report-template, reporting
period, decision, risk, notification-policy, and notification-outcome records.
Domain services enforce role capabilities, immutable revisions, advisor-final
deliverable acceptance, fixed 3-by-3 risk scoring, reporting-period template
locking, deduplicated follow-up, and auditable state changes. Existing Celery
worker/Beat processes reminders, escalation, retry, period opening, and bounded
analytics refresh. Existing project audit events and five-second frontend
polling invalidate TanStack Query data without adding push infrastructure.

The frontend adds a project Execution workspace with bounded list/detail tabs
for milestones, deliverables, decisions, and risks; expands Reports with
template, submission, revision, and analytics views; and turns the current
half-screen notification dialog into a filtered action center with preferences.
All mutations report through the global bottom-right toast, all routes enforce
server capabilities, and every new label/state is English/Chinese complete.

## Technical Context

**Language/Version**: Python 3.12+; Django 5.x; Django REST Framework 3.15+;
TypeScript 5.6; React 18.3.

**Primary Dependencies**: Existing Django, DRF, drf-spectacular, Celery 5,
django-celery-beat/results, PostgreSQL driver, Redis 5, Sentry integration,
React Router 6, TanStack Query 5, React Hook Form/Zod, Radix UI primitives,
Tailwind CSS, date-fns, and Lucide icons. No new runtime dependency.

**Storage**: Existing PostgreSQL database in CI/production and isolated Django
test databases. Redis remains a broker and bounded aggregate/query cache, never
the source of project truth. Existing uploaded material storage is referenced
as deliverable evidence; no new file store.

**Testing**: pytest/pytest-django/factory-boy, DRF contract tests,
drf-spectacular schema generation, migration and production-readiness tests,
Ruff; Vitest/React Testing Library, import-boundary tests, Playwright,
TypeScript build, ESLint, OpenAPI drift, generated-artifact, accessibility, and
responsive production UI checks.

**Target Platform**: Existing browser application and Django service deployed
through the current Docker Compose production topology with backend, frontend,
PostgreSQL, Redis, Celery worker, and Celery Beat scheduler.

**Project Type**: Full-stack web application in the existing Django monolith
and React feature-module frontend.

**Performance Goals**: Notification, execution list, and selected detail reads
complete within 3 seconds at p95. Domain mutations and project-event-driven
frontend convergence complete within 5 seconds at p95. A project with 200
milestones/deliverables, 500 report revisions, 500 decisions/risks, and a user
with 1,000 notifications retains bounded rendering and 3-second p95 filtered
reads. Analytics range is capped at 104 weekly periods per request.

**Reliability/Operations Goals**: Notification state transitions and scheduler
jobs are idempotent; duplicate business events create one active follow-up;
report periods lock exactly one template version; milestone status is derived
from required deliverable decisions; risk severity is deterministic; retries
and aggregate refresh never block authoritative project reads; all privileged
transitions are transactional with audit evidence. Worker/scheduler lag,
delivery retries/failures, unresolved action counts, period generation,
calendar projection reconciliation, and analytics failures are observable.

**Security/Compliance Constraints**: Existing bearer/session authentication,
account lifecycle, project membership, target-specific reviewer assignments,
project governance hold, and capability service remain authoritative. Every
query and deep link is project-scoped server-side. Reviewer recommendations do
not grant final acceptance. Administrators supervise through explicit
capabilities and audit but do not silently own content. User-entered text and
URLs are validated and rendered without executable markup. Exports are bounded
and permission-rechecked. Notification/audit logs exclude report bodies,
secrets, file bodies, and protected linked metadata. No new regulated-data
category is introduced.

**Constraints**: Preserve existing task, weekly report, notification, calendar,
audit, project deletion/archive, offline cache, locale, and review behavior.
Keep the existing URLs backward compatible while adding fields and nested
actions. Do not add WebSockets, a new queue, search service, analytics service,
workflow engine, arbitrary report expressions, generic user-authored
automation, or cross-feature imports of private frontend APIs.

**Scale/Scope**: Four backend domains (`projects`, `submissions`,
`notifications`, `schedules`) plus shared audit/capability services; project
dashboard and execution UI, report/review UI, notification center/preferences,
calendar projections, administrator health summaries, and focused
unit/contract/integration/component/e2e/operations coverage for AC-001..AC-018.

**Deployment/Monitoring/Degradation**: Reuse current containers, Redis,
worker/scheduler, readiness endpoints, Sentry, structured logs, audit console,
and metrics endpoint. Add scheduled work to the existing notification
registration command rather than a second scheduler. When Redis, email,
analytics cache, or calendar projection refresh is unavailable, database-backed
project records and in-app notifications remain available; the UI keeps the
last successful bounded result and exposes stale/retry state. No new secret is
required. New configurable bounds use documented environment settings with
safe defaults.

**Data Migration & Rollback**: Use additive, backward-compatible migrations.
Create the default report template, a published version, and historical weekly
report periods in bounded batches; attach existing reports to matching periods
and retain legacy narrative columns during compatibility. Existing
notifications gain defaults without fabricating acknowledgement or action
completion. Existing tasks remain unlinked until explicitly associated.
Deploy schema before code, then backfill, then enable new routes/jobs. An
application rollback leaves additive tables/columns intact and disables new
jobs/routes; it must not delete notification outcomes, report snapshots,
deliverable decisions, decisions, risks, or audit history. Destructive reverse
data migrations are prohibited.

## Constitution Check

*GATE: Passed before Phase 0 research. Re-checked after Phase 1 design.*

- **SDD Order**: PASS. `spec.md` contains all five mandatory modules, explicit
  included/excluded scope, 18 measurable acceptance criteria, and five closed
  clarifications. No planning blocker remains.
- **Review Readiness**: PASS FOR PLANNING / RELEASE BLOCKED. Product, Testing,
  and Development are assigned to NacyeZ and remain Pending. Planning and later
  implementation may proceed, but production release requires current
  revision-bound acceptance or a governed exception.
- **Required Plan Artifacts**: PASS. This workflow produces `plan.md`,
  `research.md`, `data-model.md`, `contracts/openapi.yaml`,
  `contracts/frontend-ui.md`, and `quickstart.md`.
- **Technology Governance**: PASS. No new framework, middleware, database,
  queue, storage provider, or external integration. `research.md` documents
  reuse of PostgreSQL constraints, existing Celery/Redis, project event
  polling, relational report responses, and read-only calendar projections,
  with rejected alternatives.
- **Layering and Code Baselines**: PASS. DRF views/serializers own access and
  payload shaping; project execution, report template/analytics, notification
  outcome/policy, and projection services own business orchestration; models
  and migrations own persistence; audit/common capability services own shared
  policy and evidence; React feature modules own route UI and call only their
  own or explicitly public APIs. Backward-compatible serializers preserve
  existing clients during migration.
- **TDD/Test Plan**: PASS AS PLAN. Before implementation, unit tests cover
  notification/outcome transitions and dedupe (AC-001..004), milestone
  derivation and deliverable review authority (AC-005..007), template fields,
  period locking, typed responses, and aggregates (AC-008..010), decision/risk
  lifecycle and 3-by-3 scoring (AC-011), permissions and redaction
  (AC-012..013), locale/accessibility/degradation (AC-014..016), and moderated
  journey fixtures (AC-017..018). Contract tests precede endpoint code;
  integration tests precede service wiring; component/e2e tests precede final
  route composition. No test exception is planned.
- **Security Gate**: PASS. Authentication, server-side capability checks,
  assignment-scoped reviewer reads, project isolation, current-role
  revalidation, XSS/URL validation, export limits, stale-link non-disclosure,
  audit minimization, upload/evidence reuse validation, endpoint throttling,
  bounded retries, and fail-closed privileged audit writes are explicit.
- **Performance Gate**: PASS. All large lists are cursor/page bounded; selectors
  and analytics ranges have limits; indexes cover project/status/date/owner and
  notification recipient/state/due scans; range aggregates use PostgreSQL and
  short-lived Redis caching; scheduler work is chunked with skip-locked claims;
  no request performs an unbounded backfill or fan-out.
- **Deployment/Operations Gate**: PASS. Topology and secrets are unchanged.
  Environment bounds, Beat registration, worker/readiness metrics, additive
  migration/backfill, schema-first rollout, application-first rollback,
  backup/restore coverage, OpenAPI drift, locale, performance, security,
  accessibility, and smoke checks are defined.

## Project Structure

### Documentation (this feature)

```text
specs/017-research-execution-loop/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── openapi.yaml
│   └── frontend-ui.md
└── tasks.md                 # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── projects/
│   │   ├── models.py
│   │   ├── access_services.py
│   │   ├── execution_services.py
│   │   ├── decision_risk_services.py
│   │   ├── execution_serializers.py
│   │   ├── execution_views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── migrations/
│   ├── submissions/
│   │   ├── models.py
│   │   ├── review_assignment_services.py
│   │   ├── report_template_services.py
│   │   ├── report_period_services.py
│   │   ├── report_analytics.py
│   │   ├── report_services.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── migrations/
│   ├── notifications/
│   │   ├── models.py
│   │   ├── policy_services.py
│   │   ├── outcome_services.py
│   │   ├── services.py
│   │   ├── tasks.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── migrations/
│   ├── schedules/
│   │   └── projection_services.py
│   ├── audit/
│   │   └── services.py
│   └── common/
│       ├── project_scope.py
│       └── views.py
└── tests/
    ├── unit/
    ├── contract/
    ├── integration/
    └── factories/

frontend/
├── src/
│   ├── routes/index.tsx
│   ├── features/
│   │   ├── projects/
│   │   │   ├── ProjectExecutionPage.tsx
│   │   │   ├── MilestoneList.tsx
│   │   │   ├── DeliverableDetail.tsx
│   │   │   ├── DecisionRegister.tsx
│   │   │   ├── RiskRegister.tsx
│   │   │   ├── executionApi.ts
│   │   │   └── index.ts
│   │   ├── submissions/
│   │   │   ├── WeeklyReportPage.tsx
│   │   │   ├── ReportTemplateEditor.tsx
│   │   │   ├── ReportAnalyticsPanel.tsx
│   │   │   └── api.ts
│   │   ├── notifications/
│   │   │   ├── NotificationCenter.tsx
│   │   │   ├── NotificationList.tsx
│   │   │   ├── NotificationPreferences.tsx
│   │   │   └── api.ts
│   │   └── schedules/
│   │       └── api.ts
│   └── shared/
│       ├── i18n/
│       ├── ui/
│       └── api/
└── tests/
    ├── component/
    └── e2e/
```

**Structure Decision**: Extend the existing owning domains instead of creating
a generic workflow application. Project execution and governance records stay
under `apps.projects` and `features/projects`; report templates, periods,
responses, and analytics stay under submissions; notification preferences,
delivery attempts, and business outcomes stay under notifications; schedules
consume project dates through the existing read-only projection adapter.
Cross-domain backend calls use public services, while frontend features never
import another feature's private `api.ts`.

## Phase 0 Research Decisions

The detailed evidence and alternatives are in [research.md](./research.md).
Planning is based on these resolved decisions:

1. Extend existing domains; do not introduce a workflow service.
2. Use explicit relational entities and check/unique constraints for execution
   records; use JSON only for bounded option/value payloads with server
   validation.
3. Preserve current project audit-event polling for hot refresh.
4. Use immutable deliverable submission revisions, reviewer recommendations,
   and advisor final decisions.
5. Lock report template versions when weekly reporting periods open.
6. Compute source-traceable aggregates in PostgreSQL with short Redis caching.
7. Represent decisions as immutable/superseding records and risks as
   versioned transitions using one fixed 3-by-3 matrix.
8. Keep delivery status, read state, acknowledgement, and action completion
   separate; resolve action completion from authoritative domain events.
9. Reuse existing Celery/Beat with idempotency keys and bounded database scans.
10. Add project dates to the calendar through read-only projections.

## Phase 1 Design

### Domain Ownership

- `projects`: milestones, deliverables, assignees, task links, submission
  revisions, evidence, reviewer recommendations, advisor decisions, project
  execution settings, decisions, risks, links, risk revisions, capability
  evaluation, and project event emission.
- `submissions`: report templates/fields, reporting periods, report response
  snapshots, compatibility with `WeeklyProgressReport`, analytics, exports, and
  report review lifecycle.
- `notifications`: preference profile/category preferences, project thresholds,
  notification business outcome fields, delivery attempts, dedupe, reminder,
  escalation, acknowledgement, action reconciliation, and operational metrics.
- `schedules`: read-only occurrence projections for milestone target dates,
  deliverable due dates, risk review dates, and opened report period deadlines.
- `audit`: sanitized, attributable event evidence for every privileged or
  lifecycle-sensitive change.

### Transactions and Concurrency

- Mutations accept `expectedVersion` for milestone, deliverable, template draft,
  project notification policy, and risk updates. A mismatch returns `409` with
  the current safe representation.
- Submission, recommendation, final acceptance/return, template publication,
  period opening, decision supersession, risk transition, acknowledgement, and
  action completion run in database transactions with row locks.
- Idempotency keys protect deliverable submission, final decision, report
  submission, notification acknowledgement, scheduler dispatch, and risk
  transition retries.
- Domain events are recorded only after validation and in the same transaction
  as authoritative state. Project event polling derives from committed audit
  events, so clients never observe an event for rolled-back work.

### Compatibility and Rollout

1. Deploy additive schema and indexes with new jobs disabled.
2. Create one default report template/version per project and bounded reporting
   periods for existing report weeks.
3. Attach legacy reports and materialize controlled default responses from
   `completed_work`, `blockers`, and `next_steps`; retain those columns.
4. Add new response fields and capability metadata to existing report,
   project, notification, and event contracts without removing old aliases.
5. Enable API/UI behind a deployment setting, then enable period/reminder jobs.
6. Validate metrics, OpenAPI drift, migrations, old routes, and rollback before
   production exposure.

## Required Design Artifact Checklist

- [x] `research.md` records dependency research, performance/security risk
  assessment, and technology choice comparisons.
- [x] `data-model.md` records entities, fields, constraints, indexes,
  relationships, state transitions, migration, and rollback.
- [x] `contracts/openapi.yaml` records backend interfaces and
  `contracts/frontend-ui.md` records route, role, layout, locale, live-update,
  accessibility, and degradation behavior.
- [x] `quickstart.md` records runnable validation scenarios aligned to
  AC-001..AC-018.

## Post-Design Constitution Check

- **SDD and artifacts**: PASS. Specification, research, data model, API/UI
  contracts, validation guide, and agent context are complete with no
  unresolved technical clarification.
- **Review gate**: PASS FOR IMPLEMENTATION / RELEASE BLOCKED. Product, Testing,
  and Development remain Pending; production release must fail until current
  revision acceptance or a governed exception exists.
- **Technology and layering**: PASS. The design adds no dependency or
  infrastructure and preserves domain/service/access/data/frontend boundaries.
- **TDD and traceability**: PASS AS PLAN. Quickstart and contracts identify
  test-first suites and map all AC IDs, state machines, security matrices,
  concurrency, migration, performance, locale, accessibility, and degradation.
- **Security and privacy**: PASS AS PLAN. Capability checks, assignment scope,
  admin supervision limits, stale-link non-disclosure, typed validation,
  bounded export, safe snapshots, URL sanitization, and audit are explicit.
- **Performance and operations**: PASS AS PLAN. Bounded lists/ranges, indexes,
  cache invalidation, chunked scheduler work, metrics, schema-first migration,
  application-first rollback, and backup/restore checks are defined.

## Complexity Tracking

No constitution violation or unjustified complexity is planned.
