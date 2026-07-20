# Quickstart: Dashboard Calendar and Scheduling

## Prerequisites

- Python virtual environment with backend dependencies installed, including the
  planned recurrence dependency.
- Frontend dependencies installed under `frontend/`, including the planned
  modular date utility.
- Local PostgreSQL/Redis and Celery worker/Beat setup matching the existing
  development or CI profile.
- Active administrator, advisor, and at least two student accounts.
- Two projects with different memberships plus tasks, weekly reports, and
  resource bookings covering the validation period.
- One project with a configured weekly report weekday/time/timezone and one
  active project without a report schedule.

## Backend Validation

1. Run schedule rule unit tests before and after implementation.

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/unit/test_schedule_recurrence.py tests/unit/test_schedule_permissions.py tests/unit/test_schedule_audiences.py tests/unit/test_schedule_reminders.py tests/unit/test_project_report_schedule.py
   ```

   Expected: daily/weekly/monthly rules, all-day/timezone boundaries,
   occurrence/future/series changes, owner-only privacy, staff publication,
   temporal recipient grants, advisor/admin account-search boundaries, stale
   version rejection, project report policy, and per-channel dispatch
   idempotency satisfy AC-001, AC-003, AC-005, AC-008, AC-009, AC-011, and
   AC-012.

2. Run calendar/schedule contract and OpenAPI tests.

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/contract/test_schedules_api.py tests/contract/test_calendar_api.py tests/contract/test_project_report_schedule_api.py tests/contract/test_collaboration_notifications_api.py tests/contract/test_openapi_schema.py
   ```

   Expected: period/detail/create/update/delete/publish/cancel, role-filtered
   audience options, project weekly report schedule, conflicts, revisions,
   delivery status, and event cursor match `contracts/openapi.yaml`; students
   cannot publish; advisors cannot search unrelated accounts; private direct
   reads return no content to other users or administrators.

3. Run source projection, notification, and concurrency integration tests.

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/integration/test_calendar_projections.py tests/integration/test_schedule_publication.py tests/integration/test_schedule_notifications.py tests/integration/test_schedule_concurrency.py
   ```

   Expected: authorized project/task/configured-report/booking items appear once,
   unrelated and unconfigured report items do not appear, membership changes
   open/close future recipient grants without rewriting history, publication and
   ordinary changes remain in-app-only, cancellation/reminders also send one
   email, stale writes cannot replace current state, and audit records omit
   private content (AC-002, AC-003, AC-005, AC-008, AC-009, AC-011, AC-012).

4. Run migration and performance checks.

   ```bash
   cd backend
   ../.venv/bin/python manage.py makemigrations --check --dry-run
   ../.venv/bin/python -m pytest tests/integration/test_schedule_migrations.py tests/integration/test_calendar_performance.py
   ```

   Expected: committed additive migrations are complete; calendar period queries
   satisfy the two-second p95 target with 500 accounts and 10,000 authorized
   occurrences; no source records are copied or rewritten (AC-007).

5. Verify periodic notification registration.

   ```bash
   cd backend
   ../.venv/bin/python manage.py ensure_notification_schedule
   ../.venv/bin/python manage.py check --deploy
   ```

   Expected: the existing deadline/review/delivery jobs and the new schedule
   reminder generator are enabled on the five-minute schedule with no new queue
   or secret requirement (AC-005).

## Frontend Validation

1. Run calendar component and role-boundary tests.

   ```bash
   cd frontend
   npm run test -- tests/component/dashboard-calendar.test.tsx tests/component/schedule-form.test.tsx tests/component/schedule-notifications.test.tsx tests/component/frontend-import-boundaries.test.ts
   ```

   Expected: all roles see the calendar and private planning; only staff see
   group scope; no all-member broadcast exists; teacher account options are
   manageable-project members; project report settings are staff-only; system
   items are read-only; mutation results use global toast; stale refresh retains
   data/form input; no cross-feature private API import exists
   (AC-001..AC-005, AC-009, AC-012).

2. Run browser flows and responsive/accessibility checks.

   ```bash
   cd frontend
   GRADSYNC_E2E_MODE=fullstack GRADSYNC_BACKEND_PYTHON=../.venv/bin/python npm run test:e2e -- dashboard-calendar.spec.ts schedule-publication.spec.ts production-ui.spec.ts accessibility.spec.ts collaboration-notifications.spec.ts
   ```

   Expected: students privately plan and cannot publish; advisors publish and
   update their events; administrators supervise group events without reading
   student private details; notification links open the correct date/item;
   connected sessions converge within five seconds; 390, 900, and 1440 CSS px
   have no overflow, clipped primary action, or visible text overlap
   (AC-001..AC-006, AC-008..AC-010).

3. Run standard frontend and artifact gates.

   ```bash
   cd frontend
   npm run lint
   npm run test
   npm run build
   cd ..
   sh scripts/check-openapi-contract.sh
   sh scripts/check-generated-artifacts.sh --clean
   sh scripts/check-production-readiness.sh
   ```

   Expected: lint, all component tests, type/build, contract, clean-tree, and
   production-readiness checks pass.

## Manual Role Journey

1. Sign in as a student and open `/`.
2. Confirm Month/Week/Day/Agenda views include that student's assigned task,
   configured future report deadline, and booking but exclude another student's
   private, unrelated-project, and unconfigured report items.
3. Create a recurring private item with reminders, edit one occurrence, and
   confirm operation feedback appears only in the bottom-right toast.
4. Confirm no group scope, audience, publish, group cancel, or delivery-status
   control is available to the student.
5. Sign in as an advisor, configure that project's weekly report weekday/time,
   then create a group meeting and select one project plus two of its members
   from dropdown inputs. Confirm unrelated accounts and an all-member broadcast
   option are absent, then publish after recipient-count confirmation.
6. Confirm overlapping audience membership produces one occurrence and one
   in-app publication notification per recipient and sends no publication email.
7. In a recipient session, follow the notification and confirm the dashboard
   opens the correct date and item.
8. Add a new project member and remove an old member, then edit one occurrence
   and the future series. Confirm future visibility follows current membership
   within five seconds while historical visibility remains unchanged.
9. Cancel the meeting after confirmation and verify it is visibly cancelled,
   each affected recipient receives one in-app notification and one email, and
   no obsolete reminder is generated.
10. Sign in as administrator, inspect the group publication and delivery totals,
    then attempt direct access to the student's private item and confirm no
    title, description, recurrence, or reminder content is disclosed.

## Degradation and Rollback Validation

1. Interrupt calendar API/event refresh after one successful load. Confirm the
   last successful period remains visible, stale status and manual retry appear,
   and an open form keeps valid input.
2. Retry the same reminder task multiple times. Confirm at most one in-app event
   and one email delivery exist per recipient/item/occurrence/event/offset, and
   retrying publication/ordinary-change events never sends email.
3. Suspend a recipient or remove project membership before reminder eligibility.
   Confirm the recipient is re-resolved/removed and no obsolete reminder is
   delivered.
4. Deploy migrations before application code in a staging profile, then perform
   an application-only rollback with the new tables retained. Confirm existing
   dashboard, project, task, report, booking, notification, health, and readiness
   flows continue to work.

## Release Checks

- Product, Testing, and Development reviews in `spec.md` are accepted or a
  governed release exception is recorded.
- `contracts/openapi.yaml`, generated schema, frontend API types, and
  `contracts/frontend-ui.md` remain aligned.
- Privacy matrix proves owner-only personal content against student, advisor,
  administrator, direct-ID, event-cursor, conflict, audit, and notification
  paths; audience tests prove teacher manageable-project scope and absence of
  platform-wide broadcast.
- Performance evidence covers 500 accounts, 10,000 period occurrences, bounded
  audience search, and a maximum 500-recipient publication.
- Project report policy migration/projection, Beat registration, per-channel
  reminder lag/retry/skip signals, backup compatibility, schema-first deploy,
  and application-first rollback are verified.
- No generated runtime/build artifacts remain in source scope.

## US2 Checkpoint Result (2026-07-20)

- Owner-only permission, CRUD, optimistic-version, confirmed delete, conflict,
  and occurrence-exception tests pass (`7 passed`).
- Private schedule form and existing dashboard component regressions pass
  (`17 passed`); mutation feedback uses the global toast provider.
- Dashboard private-create browser journey and supported responsive calendar
  journeys pass (`8 passed`).
- Frontend lint passes; the final production build is repeated at the release
  gate after all stories are integrated.

## US3 Checkpoint Result (2026-07-20)

- Audience eligibility, publication contracts, and publication integration:
  `9 passed`.
- Dropdown-only recipient selector and role-gated group mode component tests:
  `2 passed`.
- Advisor publication, recipient visibility, and dashboard regression browser
  flows: `10 passed`.
- Frontend production build and backend Ruff checks pass after publication
  wiring.

## US4 Checkpoint Result (2026-07-20)

- Group version, revision, cancellation, temporal membership, and API contract
  coverage: `11 passed`.
- Cancellation, revision/delivery detail, and calendar component coverage:
  `7 passed`.
- Publication, cancellation, and responsive dashboard Chromium journeys:
  `11 passed`.
- Frontend lint and production build pass with five-second event refresh.

## US5 Checkpoint Result (2026-07-20)

- Reminder eligibility, per-channel idempotency, delivery policy, retry/skip,
  and notification contract checks: `14 passed`.
- Schedule notification component and calendar/form regressions: `8 passed`.
- Notification deep-link and schedule publication/cancellation Chromium flows:
  `5 passed`.
- Beat registration includes the five-minute schedule reminder task; delivery
  outcomes are reflected in privacy-safe per-channel metrics.

## Release Gate Result (2026-07-20)

- Backend Ruff, migration dry-run, and full pytest: `429 passed`.
- Frontend ESLint, full Vitest, and production build: `164 passed`.
- Security matrix and XSS checks: `11 passed` across backend contracts and
  focused frontend components.
- Mocked schedule/notification/accessibility/production-layout Playwright:
  `41 passed` before the final dialog-focus correction; the corrected
  accessibility suite then passed `7 passed`.
- Full-stack dashboard calendar creation and responsive flows passed; the final
  corrected full-stack accessibility suite passed `5 passed, 2 skipped`.
- The feature OpenAPI check exits successfully and all schedule operations are
  present in generated schema. Existing repository-wide schema-generator
  warnings for explicitly documented query/error responses remain non-blocking.
- Generated-artifact and whitespace guards pass.
- Product, Testing, and Development acceptance remains Pending in `spec.md`;
  production release is therefore not approved.
