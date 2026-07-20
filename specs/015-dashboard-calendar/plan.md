# Implementation Plan: Dashboard Calendar and Scheduling

**Branch**: `[spec/feature-015]` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-dashboard-calendar/spec.md`

## Summary

Add a role-aware calendar to the authenticated dashboard that combines private
schedule items, staff-published group activities, and read-only projections of
project milestones, assigned task deadlines, report periods, and resource
bookings. Implement a bounded `schedules` domain in the existing Django monolith
for schedule ownership, recurrence, audience resolution, occurrence exceptions,
revisions, optimistic concurrency, reminders, and authorized calendar
aggregation. Add a project-owned weekly report schedule policy so configured
active projects generate future progress-report deadlines. Reuse the current
account/project authorization, notification and Celery Beat delivery, audit,
React Query refresh, top notification popover, and global toast patterns while
making notification delivery policy explicit: publication/ordinary changes are
in-app-only; cancellation/reminders are in-app plus email. The React dashboard
gains a responsive calendar/agenda workspace and role-correct schedule forms
without introducing a separate calendar service or push infrastructure.

## Technical Context

**Language/Version**: Python 3.12; Django 5.x; TypeScript 5.6; React 18.3.

**Primary Dependencies**: Existing Django, Django REST Framework,
drf-spectacular, Celery, django-celery-beat/results, PostgreSQL driver, Redis,
TanStack Query, React Hook Form/Zod, Radix UI primitives, Tailwind CSS, and
Lucide icons. Add `python-dateutil` for server-authoritative bounded recurrence
expansion and `date-fns` for modular frontend period/date presentation. No
full-calendar widget, WebSocket/SSE middleware, new queue, or external service.

**Storage**: Existing PostgreSQL database in CI/production and isolated test
databases. Add relational schedule item, project/account audience, temporal
recipient grant, occurrence exception, reminder, revision, and
notification-dispatch tables plus a project report schedule policy. Add explicit
notification delivery policy/status fields or choices with additive indexes and
constraints. Existing projects, tasks, reports, bookings, notifications, and
audit records remain authoritative and are not copied.

**Testing**: pytest/pytest-django, DRF contract/OpenAPI checks, migration and
performance tests, ruff; Vitest/React Testing Library, Playwright, TypeScript
build, ESLint, generated-artifact and production-readiness checks.

**Target Platform**: Existing GradSync browser application with Django API,
Celery workers/Beat, Redis, PostgreSQL, and Vite/React frontend in the current
Docker, CI, and production topology.

**Project Type**: Full-stack web application in the existing Django monolith and
React single-page frontend.

**Performance Goals**: Calendar month/week/day/agenda period changes become
visible within 2 seconds at p95 with 500 active accounts and up to 10,000
authorized occurrences in the requested period. Account/project audience
search returns a bounded first page within 2 seconds at p95. Eligible reminders
are recorded within the existing 5-minute schedule. Normal connected sessions
converge after schedule changes within 5 seconds.

**Reliability/Operations Goals**: Idempotent per-channel notification generation
and email delivery; deduplicated recipients across overlapping project/account
audiences; temporal recipient grants preserve history while membership changes
affect future occurrences; deterministic bounded recurrence expansion;
optimistic concurrency rejects stale writes; last-successful calendar data
remains visible on refresh failure; in-progress forms survive refresh; audit
records omit private item content; rollback preserves historical schedule and
notification evidence.

**Security/Compliance Constraints**: Authenticated active accounts only.
Private schedule content is owner-only, including against administrator list,
detail, audit, and notification interfaces. Students cannot publish group
items. Advisors can manage only their own group publications unless separately
authorized; administrators can supervise all group publications. Advisor
recipient search is limited to active members of projects the advisor can
manage; administrators may search any active account with minimized identity
fields. There is no platform-wide all-account broadcast. Every period, detail,
recipient search, mutation, publication, reminder, event, and delivery status
read is server-authorized. Group publication and privileged actions are audited
without private content. No new regulated-data scope or secret.

**Constraints**: Preserve existing dashboard navigation, project visibility,
task/report/booking ownership, notification center, global toast behavior,
email delivery, health/readiness, and frontend import boundaries. System
projections are read-only and link back to their owning feature. Recurrence is
limited to none/daily/weekly/monthly, requires an end date, is capped at two
years and 1,000 generated occurrences per series, and supports occurrence,
future-series, and whole-series changes. Requested calendar windows are capped
at 62 days except agenda pagination. Publication resolves at most 500 recipients
per operation. Supported reminder offsets are 0, 15, 30, 60, 1,440, and 10,080
minutes. Group audiences require at least one selected project or direct
account; selected-project membership is re-resolved for future occurrences and
never rewrites historical grants. Each active project has at most one optional
weekly report weekday/local-time/timezone policy; unconfigured and archived
projects generate no future report deadlines.

**Scale/Scope**: New `apps.schedules` models/services/serializers/views/URLs and
migrations; additive notification event types/tasks and audit integration;
an additive project report schedule policy in `apps.submissions`; read-only
adapters over projects/tasks/submissions/resources; dashboard and new frontend
`features/schedules`; unit, contract, integration, component, browser,
performance, accessibility, migration, readiness, and rollback validation.

**Deployment/Monitoring/Degradation**: Same web/worker/scheduler topology. Add
the schedule reminder generator to the existing 5-minute Celery Beat setup and
route it through the existing notifications queue. No new environment variables,
ports, services, secrets, or manual operators. Logs/metrics/audit distinguish
period query failure, recurrence limit rejection, audience resolution failure,
stale version conflict, authorization denial, reminder lag, retry, skip, and
duplicate prevention by delivery channel without logging private
titles/descriptions. In-app-only events are never claimed by email delivery;
cancellation/reminder email uses the existing retry path. On API/event refresh
failure, the frontend retains the last successful period, marks it stale,
retries with bounded backoff, and exposes manual refresh.

**Data Migration & Rollback**: Add new schedule tables, project report schedule
policy, schedule notification event types, and explicit delivery policy/status
through forward-only additive migrations. Existing notification rows default to
their current email-capable behavior. Migrations do not backfill report policies
or rewrite projects, tasks, reports, bookings, notifications, or audit records.
Deploy schema before code. Application rollback stops schedule routes and
periodic generation while retaining new tables and historical notification/audit
records; database reversal is optional only after backup and confirmation that
schedule history may be discarded. Existing module behavior remains intact
through both paths.

## Constitution Check

*GATE: Passed before Phase 0 research. Re-check after Phase 1 design.*

- **SDD Order**: PASS. `spec.md` exists, contains all five mandatory modules,
  included/excluded scope, measurable acceptance criteria, privacy boundaries,
  and no unresolved clarification.
- **Review Readiness**: PASS FOR PLANNING / RELEASE BLOCKED. Product, Testing,
  and Development are recorded as Pending. Planning and implementation may
  proceed, but production release requires acceptance or a governed exception.
- **Required Plan Artifacts**: PASS. This workflow produces `plan.md`,
  `research.md`, `data-model.md`, `contracts/openapi.yaml`,
  `contracts/frontend-ui.md`, and `quickstart.md`.
- **Technology Governance**: PASS. `research.md` compares recurrence/date
  libraries, full calendar widgets, live refresh transports, occurrence storage,
  source projection strategies, and reminder integration. Two bounded date
  dependencies are justified; no new framework, database, storage, queue, or
  external integration is introduced.
- **Layering and Code Baselines**: PASS. DRF views/serializers own request and
  response shaping; schedule authorization, recurrence, audience, mutation,
  projection, conflict, reminder, and event services own business rules; models
  and migrations own persistence/constraints/indexes; submissions owns the
  project report schedule policy; notification/audit services own channel-aware
  side effects; `features/schedules` owns calendar presentation and imports only
  public/shared APIs. Existing source modules remain authoritative and
  backward-compatible.
- **TDD/Test Plan**: PASS AS PLAN. Before implementation: unit tests for
  recurrence/timezone boundaries, audience deduplication, temporal recipient
  grants, advisor/admin search boundaries, project report policy, privacy,
  transition, optimistic concurrency, conflict warnings, and per-channel
  reminder idempotency (AC-001..AC-005, AC-008, AC-009, AC-011, AC-012);
  contract tests for period, detail, create/update/delete/publish/cancel,
  role-filtered audience search, project report policy, conflicts, event cursor,
  and delivery status (AC-001..AC-005, AC-008, AC-009, AC-012); integration tests
  for source projections, dynamic membership/account changes, recurrence
  exceptions, in-app-only versus email delivery, notification retries, audit
  minimization, migrations, performance, and rollback preservation
  (AC-002..AC-005, AC-007..AC-009, AC-011, AC-012); frontend
  component tests for role controls, period navigation, detail/form behavior,
  source distinction, toast-only feedback, stale state, and 390-pixel layout
  (AC-001, AC-002, AC-004, AC-006); Playwright for each role, private isolation,
  staff publication, notification navigation, responsive layout, accessibility,
  and live convergence (AC-001..AC-006, AC-009, AC-010); readiness/smoke checks
  for Beat registration and migration plan.
- **Security Gate**: PASS. Authentication, owner-only private reads, staff-only
  group publication, publisher/admin mutation policy, server-side dynamic
  recipient revalidation, teacher search limited to manageable-project members,
  administrator search limited to active accounts, no all-account broadcast,
  bounded search, XSS-safe text rendering, action-path authorization, rate
  limiting, privacy-safe audit/logging, stale-write rejection, and per-channel
  notification deduplication are required. No upload surface exists.
- **Performance Gate**: PASS. Period queries are bounded to 62 days; agenda uses
  pagination; audience options and recipients are capped; hot predicates have
  composite indexes; source adapters use select/prefetch/union-safe bounded
  reads; recurrence expands only within the requested window; notification work
  is chunked. No shared cache is introduced because private authorization makes
  invalidation risk outweigh current scale benefit.
- **Deployment/Operations Gate**: PASS. Existing topology and notification queue
  are reused; no new secrets/configuration. Additive schema-first migration,
  Beat schedule registration, privacy-safe signals, retry/degradation behavior,
  backup/restore compatibility, smoke checks, performance validation, and
  application-first rollback are documented.

## Project Structure

### Documentation (this feature)

```text
specs/015-dashboard-calendar/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── frontend-ui.md
└── tasks.md              # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── schedules/
│   │   ├── models.py
│   │   ├── recurrence.py
│   │   ├── permissions.py
│   │   ├── projection_services.py
│   │   ├── reminder_services.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/
│   ├── notifications/
│   │   ├── models.py
│   │   ├── services.py
│   │   └── tasks.py
│   ├── submissions/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   └── views.py
│   └── audit/
│       └── services.py
├── gradsync/
│   ├── settings/base.py
│   └── urls.py
└── tests/
    ├── unit/
    ├── contract/
    └── integration/

frontend/
├── src/
│   ├── app/HomePage.tsx
│   ├── features/schedules/
│   │   ├── api.ts
│   │   ├── CalendarAgenda.tsx
│   │   ├── CalendarGrid.tsx
│   │   ├── CalendarToolbar.tsx
│   │   ├── ScheduleDetailPanel.tsx
│   │   ├── ScheduleFormDialog.tsx
│   │   ├── ScheduleRecipientSelector.tsx
│   │   └── useCalendarLiveRefresh.ts
│   └── shared/ui/
└── tests/
    ├── component/
    └── e2e/
```

**Structure Decision**: Add a dedicated schedules domain because schedule
ownership, recurrence, audiences, reminders, and privacy form a coherent
business boundary not owned by projects or notifications. Keep calendar UI in
`features/schedules` and compose it into `HomePage`; do not place schedule API
logic in the home page or import private APIs from projects/tasks/resources/
submissions. The submissions domain owns the project weekly report policy;
backend calendar projection adapters read it and other source domains through
public models/services without transferring data ownership.

## Required Design Artifact Checklist

- [x] `research.md` records dependency research, performance/security risk
  assessment, and technology choice comparisons.
- [x] `data-model.md` records entities, fields, constraints, indexes,
  relationships, state transitions, and migration approach.
- [x] `contracts/openapi.yaml` records calendar, schedule, audience, conflict,
  event, and delivery-status API contracts; `contracts/frontend-ui.md` records
  route, role, layout, interaction, feedback, and accessibility contracts.
- [x] `quickstart.md` records runnable validation scenarios aligned to AC IDs.

## Post-Design Constitution Check

- **SDD and artifact gates**: PASS. Specification, research, data model, API/UI
  contracts, and validation guide are complete with no unresolved technical
  clarification.
- **Review gate**: PASS FOR IMPLEMENTATION / RELEASE BLOCKED. Product, Testing,
  and Development acceptance remains Pending.
- **Technology/layering gates**: PASS. New dependencies are small and bounded;
  recurrence is server-authoritative; no new service, queue, or transport is
  added; ownership boundaries and frontend import boundaries are explicit.
- **Testing/security/performance gates**: PASS AS PLAN. TDD coverage maps to all
  ACs, including owner-only privacy against administrators, recurrence/timezone,
  role-bounded recipient selection, dynamic future membership, immutable
  historical grants, project weekly report policy, channel-specific delivery,
  deduplication, concurrency, 10,000-occurrence period performance, and
  390-pixel overlap checks.
- **Operations gate**: PASS AS PLAN WITH REVIEW RISK. Schema-first migration,
  existing Beat/queue reuse, idempotent retries, health/readiness preservation,
  privacy-safe signals, backup compatibility, smoke validation, and
  application-first rollback are documented.

## Complexity Tracking

No constitution violations require justification.
