# Tasks: Dashboard Calendar and Scheduling

**Input**: Design documents from `/specs/015-dashboard-calendar/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `contracts/frontend-ui.md`, `quickstart.md`

**Tests**: TDD is mandatory. Test tasks in every phase must be written and shown
to fail for the missing behavior before their paired implementation task begins.

**Organization**: Tasks are grouped by user story and are each scoped to no more
than eight hours. Every task includes an exact ownership path, acceptance/gate
traceability, and a concrete self-check.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add bounded dependencies and create module/test structure without
business behavior.

- [X] T001 [P] [Backend] Add `python-dateutil>=2.9,<3` to `backend/pyproject.toml`; self-check: the project virtual environment installs/imports `dateutil` and existing dependency checks pass (Gate: Technology Governance)
- [X] T002 [P] [Frontend] Add modular `date-fns` dependency to `frontend/package.json` and `frontend/package-lock.json`; self-check: `npm install` is clean and a TypeScript import resolves without adding a calendar widget (Gate: Technology Governance)
- [X] T003 [P] [Backend] Create the `backend/apps/schedules/` package skeleton, app config, empty migrations package, and register routes/app ownership in `backend/gradsync/settings/base.py` and `backend/gradsync/urls.py`; self-check: `manage.py check` imports the app with no endpoint behavior implemented (Gate: Layering)
- [X] T004 [P] [Frontend] Create public module stubs in `frontend/src/features/schedules/api.ts` and component file structure from `plan.md`; self-check: frontend import-boundary tests recognize `features/schedules` and no private cross-feature imports exist (Gate: Layering)
- [X] T005 [P] [Test] Add schedule and project-report-policy factory scaffolding in `backend/tests/factories/schedules.py` and calendar API mock builders in `frontend/tests/e2e/api-mocks.ts`; self-check: factories/mocks import without creating production data (Gate: Test Isolation)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish persistence, recurrence, authorization, delivery policy,
event invalidation, and shared client contracts required by all stories.

**Critical**: No user-story implementation begins until this phase passes.

### Tests First

- [X] T006 [P] [Test] Write failing schedule entity constraint/state tests in `backend/tests/unit/test_schedule_model_rules.py` for timed/all-day exclusivity, bounded recurrence, reminders, audiences, temporal grants, exceptions, revisions, and versions; self-check: tests fail because models/constraints are absent (AC: AC-008, AC-009)
- [X] T007 [P] [Test] Write failing notification delivery-policy tests in `backend/tests/unit/test_schedule_notification_policy.py` for `in_app`, `in_app_email`, `in_app_only`, event types, and per-channel uniqueness; self-check: publication/change email attempts fail the test before implementation (AC: AC-005)
- [X] T008 [P] [Test] Write failing recurrence/timezone tests in `backend/tests/unit/test_schedule_recurrence.py` for daily/weekly/monthly, month end, DST, all-day exclusive end, two-year horizon, and 1,000-occurrence cap; self-check: each boundary has a deterministic expected occurrence set (AC: AC-002, AC-008)
- [X] T009 [P] [Test] Write failing forward/rollback migration tests in `backend/tests/integration/test_schedule_migrations.py` covering new schedule tables, project report policy, existing Notification defaults, and preservation of project/task/report/booking rows; self-check: test proves no default report policy or source-row rewrite occurs (AC: AC-011, AC-012; Gate: Migration)

### Shared Implementation

- [X] T010 [Backend] Implement `ScheduleItem`, `ScheduleAudience`, and temporal `ScheduleRecipientGrant` with ownership, recurrence, audience, interval constraints, and indexes in `backend/apps/schedules/models.py`; self-check: T006 core model tests pass and only one open grant per schedule/user is allowed (AC: AC-003, AC-008, AC-009)
- [X] T011 [Backend] Implement `ScheduleOccurrenceException`, `ScheduleReminder`, `ScheduleRevision`, and `ScheduleNotificationDispatch` with sparse-occurrence and per-channel uniqueness constraints in `backend/apps/schedules/models.py`; self-check: T006 exception/reminder/revision/dispatch tests pass without weakening T010 constraints (AC: AC-005, AC-008, AC-011)
- [X] T012 [P] [Backend] Implement one-to-one `ProjectReportSchedule` with weekday/time/timezone/version fields and active-project validation in `backend/apps/submissions/models.py`; self-check: unconfigured projects remain row-free and archived-project updates are rejected (AC: AC-012)
- [X] T013 [P] [Backend] Add schedule event types, `delivery_policy`, and exact `in_app_only` status behavior to `backend/apps/notifications/models.py`; self-check: existing notification rows retain email-capable defaults and T007 policy tests pass (AC: AC-005)
- [X] T014 [Backend] Generate and review additive migrations in `backend/apps/schedules/migrations/`, `backend/apps/submissions/migrations/`, and `backend/apps/notifications/migrations/`; self-check: T009 passes and `makemigrations --check --dry-run` reports no drift (AC: AC-011, AC-012; Gate: Migration)
- [X] T015 [Backend] Implement bounded server-authoritative occurrence expansion and local/UTC conversion in `backend/apps/schedules/recurrence.py`; self-check: T008 passes without client-derived recurrence truth (AC: AC-002, AC-007, AC-008)
- [X] T016 [Backend] Implement owner/publisher/admin/project/member authorization helpers and role-filtered recipient eligibility in `backend/apps/schedules/permissions.py`; self-check: administrators cannot read another user's private item and advisors cannot resolve unrelated accounts (AC: AC-001, AC-003, AC-009)
- [X] T017 [P] [Backend] Define shared schedule, occurrence, recurrence, audience, capability, conflict, and version-error serializers in `backend/apps/schedules/serializers.py`; self-check: serialized names match `contracts/openapi.yaml` and reject raw all-account input (AC: AC-003, AC-008)
- [X] T018 [P] [Backend] Add privacy-minimized schedule audit event helpers in `backend/apps/audit/services.py`; self-check: group actions record actor/scope/outcome/time while private title, description, recurrence, and reminders never enter audit payloads (AC: AC-009, AC-011)
- [X] T019 [P] [Frontend] Implement calendar API types, query keys, ISO period parsing, date-fns helpers, and safe error mapping in `frontend/src/features/schedules/api.ts`; self-check: TypeScript types align with all OpenAPI occurrence/capability/error fields and expose no project private API imports (AC: AC-002, AC-008)
- [X] T020 [P] [Backend] Implement visibility-filtered opaque calendar event cursor primitives in `backend/apps/schedules/event_services.py`; self-check: private cursor events are owner-only and contain no title/description (AC: AC-009; Gate: Live Convergence)

**Checkpoint**: Schema, authorization, recurrence, contracts, and delivery-policy
foundations pass before story work begins.

---

## Phase 3: User Story 1 - View a Unified Dashboard Calendar (Priority: P1)

**Goal**: Show every authenticated role an authorized month/week/day/agenda
calendar combining personal/group schedule occurrences and read-only project,
task, configured report, submitted report, and booking projections.

**Independent Test**: Seed all source types plus unrelated/private records,
configure one project weekly report policy, and verify each role sees only the
correct occurrences at 390, 900, and 1440 CSS px; an unconfigured/archived
project generates no future report deadline.

### Tests First

- [X] T021 [P] [US1] [Test] Write failing calendar period/event cursor contract tests in `backend/tests/contract/test_calendar_api.py`; self-check: tests cover 62-day limit, agenda cursor, source filters, capabilities, auth, and safe event cursors before endpoints exist (AC: AC-001, AC-002, AC-007, AC-009)
- [X] T022 [P] [US1] [Test] Write failing project report schedule contract tests in `backend/tests/contract/test_project_report_schedule_api.py`; self-check: advisor/admin create-update-delete, student read-only, stale version, archived project, and unconfigured `204` paths fail before implementation (AC: AC-008, AC-012)
- [X] T023 [P] [US1] [Test] Write failing cross-source projection/privacy integration tests in `backend/tests/integration/test_calendar_projections.py`; self-check: project/task/report/booking visibility matrices and missing/deleted source paths are asserted (AC: AC-002, AC-009, AC-012)
- [X] T024 [P] [US1] [Test] Write failing 500-account/10,000-occurrence period performance test in `backend/tests/integration/test_calendar_performance.py`; self-check: query-count and two-second p95 budgets are explicit and no unbounded range succeeds (AC: AC-007)
- [X] T025 [P] [US1] [Test] Write failing dashboard calendar component tests in `frontend/tests/component/dashboard-calendar.test.tsx`; self-check: views, filters, detail selection, source/status labels, stale/empty/error states, keyboard behavior, and read-only source actions are covered (AC: AC-001, AC-002, AC-006)
- [X] T026 [P] [US1] [Test] Write failing role/view browser journey in `frontend/tests/e2e/dashboard-calendar.spec.ts`; self-check: admin/advisor/student source visibility, configured report deadline, notification query context, and responsive layout are asserted (AC: AC-001, AC-002, AC-006, AC-012)

### Implementation

- [X] T027 [P] [US1] [Backend] Implement project milestone and assigned/staff-visible task adapters in `backend/apps/schedules/projection_services.py`; self-check: unauthorized projects/tasks emit neither occurrence nor action path (AC: AC-002, AC-009)
- [X] T028 [P] [US1] [Backend] Implement configured future and submitted report projection adapter in `backend/apps/schedules/projection_services.py`; self-check: only configured active projects generate future deadlines for current members (AC: AC-002, AC-012)
- [X] T029 [P] [US1] [Backend] Implement requester/manager-authorized booking projection adapter in `backend/apps/schedules/projection_services.py`; self-check: cancelled/missing/unrelated booking behavior matches Resources authorization (AC: AC-002, AC-009)
- [X] T030 [US1] [Backend] Implement project report schedule service, serializers, and audit/version behavior in `backend/apps/submissions/services.py` and `backend/apps/submissions/serializers.py`; self-check: T022 business paths pass and historical reports are unchanged (AC: AC-008, AC-011, AC-012)
- [X] T031 [US1] [Backend] Expose `/projects/{projectId}/report-schedule/` through `backend/apps/submissions/views.py` and `backend/apps/submissions/urls.py`; self-check: T022 contract responses match OpenAPI exactly (AC: AC-012)
- [X] T032 [US1] [Backend] Implement authorized bounded calendar aggregation and occurrence/event serializers in `backend/apps/schedules/projection_services.py` and `backend/apps/schedules/serializers.py`; self-check: duplicate source occurrences collapse and T023/T024 pass (AC: AC-002, AC-007, AC-009)
- [X] T033 [US1] [Backend] Expose `/calendar/occurrences/` and `/calendar/events/` in `backend/apps/schedules/views.py` and `backend/apps/schedules/urls.py` with rate limits and stable errors; self-check: T021 passes and oversized windows return field-level validation (AC: AC-002, AC-007)
- [X] T034 [P] [US1] [Frontend] Implement stable calendar toolbar, month/week/day grids, and agenda list in `frontend/src/features/schedules/CalendarToolbar.tsx`, `CalendarGrid.tsx`, and `CalendarAgenda.tsx`; self-check: keyboard navigation and source distinctions do not rely on color alone (AC: AC-002, AC-006)
- [X] T035 [P] [US1] [Frontend] Implement capability-driven occurrence detail region in `frontend/src/features/schedules/ScheduleDetailPanel.tsx`; self-check: system items are read-only and absent `actionPath` never creates a link (AC: AC-002, AC-009)
- [X] T036 [US1] [Frontend] Compose the calendar workspace into `frontend/src/app/HomePage.tsx` and add stable responsive workspace rules in `frontend/src/styles/globals.css`; self-check: T025/T026 dashboard flows pass with fixed scrolling regions and no overlap/overflow at all supported widths (AC: AC-001, AC-006)
- [X] T037 [US1] [Frontend] Add role-aware project weekly report schedule controls and read-only student summary to `frontend/src/features/submissions/WeeklyReportPage.tsx`; self-check: configured/unconfigured/archived/stale-version flows use global toast and satisfy T022/T026 (AC: AC-004, AC-008, AC-012)

**Checkpoint**: US1 is a deployable MVP: unified authorized calendar plus
project-configured weekly report deadlines works without authored-item mutation.

---

## Phase 4: User Story 2 - Plan a Private Schedule (Priority: P1)

**Goal**: Let every authenticated user privately create, edit, complete, and
confirmed-delete one-time/all-day/bounded-recurring items with conflict warnings
and owner-only details.

**Independent Test**: Each role creates and mutates a private series and one
occurrence; every other account including administrator fails list/detail/direct
access, while valid form input and global toast feedback are preserved.

### Tests First

- [X] T038 [P] [US2] [Test] Extend failing owner-only and lifecycle tests in `backend/tests/unit/test_schedule_permissions.py`; self-check: private list/detail/conflict/event/audit access is denied to every non-owner including admin (AC: AC-008, AC-009)
- [X] T039 [P] [US2] [Test] Write failing private schedule CRUD/complete/conflict contract tests in `backend/tests/contract/test_schedules_api.py`; self-check: timed/all-day/recurring, occurrence/future/series scopes, confirmation, validation, and stale versions are covered (AC: AC-004, AC-008, AC-009)
- [X] T040 [P] [US2] [Test] Write failing private recurrence mutation integration tests in `backend/tests/integration/test_private_schedule_planning.py`; self-check: unaffected occurrences and form-correctable error payloads are asserted across timezone/month-end cases (AC: AC-004, AC-008)
- [X] T041 [P] [US2] [Test] Write failing private form/detail component tests in `frontend/tests/component/schedule-form.test.tsx`; self-check: role scope, recurrence controls, conflict confirmation, deletion scope, stale state, focus, and toast-only operation feedback are covered (AC: AC-004, AC-006, AC-008)
- [X] T042 [P] [US2] [Test] Write failing private planning browser flow in `frontend/tests/e2e/dashboard-calendar.spec.ts`; self-check: student/advisor/admin private journeys and cross-session direct-ID privacy are covered (AC: AC-004, AC-009, AC-010)

### Implementation

- [X] T043 [US2] [Backend] Implement transactional private create/update/complete/delete services and sparse occurrence/future split handling in `backend/apps/schedules/services.py`; self-check: T038/T040 pass and `expectedVersion` rejects stale writes (AC: AC-008, AC-009)
- [X] T044 [P] [US2] [Backend] Implement safe visible-overlap conflict detection in `backend/apps/schedules/conflict_services.py`; self-check: only owner-visible titles are returned and ordinary overlap remains non-blocking (AC: AC-008, AC-009)
- [X] T045 [US2] [Backend] Implement private schedule serializers and CRUD/conflict actions in `backend/apps/schedules/serializers.py` and `backend/apps/schedules/views.py`; self-check: T039 matches OpenAPI and group-only actions remain forbidden (AC: AC-004, AC-008, AC-009)
- [X] T046 [P] [US2] [Frontend] Implement accessible private create/edit form and recurrence/reminder controls in `frontend/src/features/schedules/ScheduleFormDialog.tsx`; self-check: invalid fields remain local while mutation outcomes use `useAppFeedback().notify` (AC: AC-004, AC-006)
- [X] T047 [P] [US2] [Frontend] Implement recurring change-scope and destructive confirmation flows in `frontend/src/features/schedules/ScheduleDetailPanel.tsx`; self-check: this/future/series choices are explicit and group delete is unavailable (AC: AC-004, AC-008)
- [X] T048 [US2] [Frontend] Wire private create/update/complete/delete/conflict mutations and query invalidation in `frontend/src/features/schedules/api.ts` and `frontend/src/app/HomePage.tsx`; self-check: last calendar state and open-form input survive background refresh/failure (AC: AC-004, AC-008)
- [X] T049 [US2] [Validation] Run and document US2 checkpoint results in `specs/015-dashboard-calendar/quickstart.md`; self-check: private lifecycle, privacy, toast, recurrence, and responsive tests pass independently (AC: AC-004, AC-006, AC-008, AC-009)

**Checkpoint**: US2 private planning is independently usable by every role and
does not expose content to administrators or other users.

---

## Phase 5: User Story 3 - Publish a Group Schedule (Priority: P1)

**Goal**: Let advisors publish to selected manageable projects/members and
administrators publish to selected projects/active accounts, with no all-account
broadcast, deduplicated temporal grants, and in-app-only publication notices.

**Independent Test**: Publish overlapping project/account audiences, verify one
future occurrence and one in-app notice per recipient, zero publication emails,
teacher search isolation, student denial, and administrator active-account scope.

### Tests First

- [x] T050 [P] [US3] [Test] Write failing audience eligibility/deduplication/grant tests in `backend/tests/unit/test_schedule_audiences.py`; self-check: teacher unrelated accounts and all-account scope are rejected while overlapping selections create one open grant (AC: AC-003, AC-009)
- [x] T051 [P] [US3] [Test] Extend failing publish/audience option contract tests in `backend/tests/contract/test_schedules_api.py`; self-check: advisor/admin/student matrices, bounded dropdown paging, raw stale IDs, recipient caps, and publish conversion are covered (AC: AC-001, AC-003)
- [x] T052 [P] [US3] [Test] Write failing publication integration tests in `backend/tests/integration/test_schedule_publication.py`; self-check: transaction rollback, deduplication, temporal grant start, audit minimization, in-app notification, and zero email are asserted (AC: AC-003, AC-005, AC-009, AC-011)
- [x] T053 [P] [US3] [Test] Write failing audience selector/role component tests in `frontend/tests/component/schedule-form.test.tsx`; self-check: candidates remain dropdown-only, no all-member control exists, duplicates disable, and student group mode is absent (AC: AC-001, AC-003, AC-006)
- [x] T054 [P] [US3] [Test] Write failing advisor/admin/student publication browser flow in `frontend/tests/e2e/schedule-publication.spec.ts`; self-check: selected project/member publication and recipient notification visibility are covered end to end (AC: AC-001, AC-003, AC-005, AC-010)

### Implementation

- [x] T055 [US3] [Backend] Implement bounded project/account option search and role revalidation in `backend/apps/schedules/audience_services.py`; self-check: advisor results are only active manageable-project members and admin results are active accounts with minimized fields (AC: AC-003, AC-009)
- [x] T056 [US3] [Backend] Implement atomic audience resolution and deduplicated temporal grant creation in `backend/apps/schedules/audience_services.py`; self-check: overlap merges source evidence and no all-account path exists (AC: AC-003)
- [x] T057 [US3] [Backend] Implement atomic direct-group create and private-to-group publish transitions with first revision in `backend/apps/schedules/services.py`; self-check: transaction rollback preserves private scope and T052 publication state/grant assertions pass (AC: AC-003, AC-008, AC-011)
- [x] T058 [US3] [Backend] Implement publication audit and in-app-only notification dispatch in `backend/apps/schedules/reminder_services.py` and `backend/apps/audit/services.py`; self-check: T052 proves one top notification per recipient and publication never enters email delivery (AC: AC-005, AC-009, AC-011)
- [x] T059 [US3] [Backend] Expose audience options and publish/create-group contracts in `backend/apps/schedules/views.py` and `backend/apps/schedules/urls.py`; self-check: T051 passes with `403/409/429` behavior and no raw account-directory leak (AC: AC-001, AC-003, AC-009)
- [x] T060 [P] [US3] [Frontend] Implement dropdown-based project/account multi-selector and selected-option chips in `frontend/src/features/schedules/ScheduleRecipientSelector.tsx`; self-check: list opens from input, is keyboard usable, bounded, and never permanently displays all candidates (AC: AC-003, AC-006)
- [x] T061 [P] [US3] [Frontend] Add staff-only group mode, recipient preview, dynamic-membership explanation, and explicit publish confirmation to `frontend/src/features/schedules/ScheduleFormDialog.tsx`; self-check: teacher/admin capabilities come from API/auth and student DOM has no publish control (AC: AC-001, AC-003)
- [x] T062 [US3] [Frontend] Wire audience search and publish mutations in `frontend/src/features/schedules/api.ts`; self-check: stale/ineligible recipients preserve selections for correction and success/failure uses global toast (AC: AC-003, AC-004)
- [x] T063 [US3] [Backend] Add group publication and audience audit/operational signals in `backend/apps/audit/services.py` and `backend/apps/schedules/services.py`; self-check: actor/scope/count/outcome/time are queryable without titles, descriptions, emails, or private reminder content (AC: AC-009, AC-011)
- [x] T064 [US3] [Validation] Run and document US3 checkpoint results in `specs/015-dashboard-calendar/quickstart.md`; self-check: role search, no broadcast, deduplication, in-app-only notice, audit, and browser publication pass independently (AC: AC-001, AC-003, AC-005, AC-009, AC-011)

**Checkpoint**: US3 publication works with role-correct bounded audiences and no
email fatigue or platform-directory exposure.

---

## Phase 6: User Story 4 - Change or Cancel Published Activities (Priority: P2)

**Goal**: Support occurrence/future/series changes, dynamic project membership,
immutable historical grants, revisions, administrator supervision, and confirmed
cancellation with in-app plus email delivery.

**Independent Test**: Change and cancel a recurring publication while adding,
removing, and rejoining project members; future access follows membership,
history remains stable, stale writes fail, and cancellation sends one notice per
configured channel.

### Tests First

- [x] T065 [P] [US4] [Test] Write failing group recurrence/version/revision tests in `backend/tests/unit/test_schedule_group_changes.py`; self-check: occurrence/future/series split, stale versions, publisher/admin policy, and cancelled lifecycle are covered (AC: AC-008, AC-011)
- [x] T066 [P] [US4] [Test] Write failing temporal membership integration tests in `backend/tests/integration/test_schedule_publication.py`; self-check: join/remove/rejoin opens and closes grants without changing prior intervals or historical notification recipients (AC: AC-003, AC-009)
- [x] T067 [P] [US4] [Test] Extend failing update/cancel/revision/delivery contract tests in `backend/tests/contract/test_schedules_api.py`; self-check: current safe state on `409`, group delete denial, cancellation confirmation, and admin override are asserted (AC: AC-005, AC-008, AC-011)
- [x] T068 [P] [US4] [Test] Write failing change/cancel/revision UI tests in `frontend/tests/component/schedule-form.test.tsx` and `frontend/tests/e2e/schedule-publication.spec.ts`; self-check: focus/form retention, scope choice, cancelled state, and delivery totals are covered (AC: AC-004, AC-005, AC-006, AC-008)

### Implementation

- [x] T069 [US4] [Backend] Implement transactional group occurrence/future/series updates and revision generation in `backend/apps/schedules/services.py`; self-check: T065 passes and no newer version is overwritten (AC: AC-008, AC-011)
- [x] T070 [US4] [Backend] Implement membership-triggered/before-read/before-reminder grant re-resolution in `backend/apps/schedules/audience_services.py`; self-check: T066 proves future-only changes and immutable closed grants (AC: AC-003, AC-009)
- [x] T071 [US4] [Backend] Implement confirmed occurrence/future/series cancellation transitions and cancellation revisions in `backend/apps/schedules/services.py`; self-check: cancelled occurrences remain historically visible and generate no future reminders (AC: AC-008, AC-011)
- [x] T072 [US4] [Backend] Implement recipient-removal notices and `in_app_email` cancellation dispatch in `backend/apps/schedules/reminder_services.py`; self-check: cancellation yields one top notification and one email per affected recipient while ordinary changes remain in-app-only (AC: AC-005)
- [x] T073 [US4] [Backend] Expose update/cancel/revisions/delivery-status actions in `backend/apps/schedules/views.py`, `serializers.py`, and `urls.py`; self-check: T067 matches OpenAPI and private delivery history stays owner-only (AC: AC-005, AC-008, AC-009)
- [x] T074 [P] [US4] [Frontend] Implement recurring scope, current-version reconciliation, revision history, and cancellation confirmation in `frontend/src/features/schedules/ScheduleDetailPanel.tsx`; self-check: stale form data is not auto-discarded and group delete never appears (AC: AC-004, AC-008)
- [x] T075 [P] [US4] [Frontend] Implement publisher/admin delivery summary and cancelled occurrence presentation in `frontend/src/features/schedules/ScheduleDetailPanel.tsx`; self-check: in-app and email totals are distinct and recipients do not receive private account lists (AC: AC-005, AC-009)
- [x] T076 [US4] [Frontend] Implement five-second event invalidation with stale retention/manual retry in `frontend/src/features/schedules/useCalendarLiveRefresh.ts` and wire it in `frontend/src/app/HomePage.tsx`; self-check: cross-session change converges without moving focus, closing forms, or clearing input (AC: AC-004, AC-008; Gate: Live Convergence)

**Checkpoint**: US4 changes/cancellation remain correct under concurrency and
membership churn while preserving historical evidence.

---

## Phase 7: User Story 5 - Receive Relevant Schedule Reminders (Priority: P2)

**Goal**: Generate idempotent due reminders every five minutes, show them in the
top notification center, send exactly one email, skip obsolete recipients, and
deep-link to authorized calendar/source context.

**Independent Test**: Re-run reminder generation/delivery around due, cancelled,
completed, expired, removed-member, failed-email, and retry cases; each eligible
recipient gets one in-app reminder and one email, and no obsolete/duplicate
delivery occurs.

### Tests First

- [x] T077 [P] [US5] [Test] Write failing reminder eligibility/idempotency tests in `backend/tests/unit/test_schedule_reminders.py`; self-check: every offset, timed/all-day occurrence, cancellation/completion/expiry, and per-channel unique key is covered (AC: AC-005)
- [x] T078 [P] [US5] [Test] Write failing channel/retry integration tests in `backend/tests/integration/test_schedule_notifications.py`; self-check: publication/change never email, cancellation/reminder email retry, removed recipients skip, and duplicate task execution are asserted (AC: AC-003, AC-005)
- [x] T079 [P] [US5] [Test] Extend failing notification contract tests in `backend/tests/contract/test_collaboration_notifications_api.py`; self-check: schedule event types, `deliveryPolicy`, `in_app_only`, action path, and privacy-safe failure fields match OpenAPI (AC: AC-005, AC-009)
- [x] T080 [P] [US5] [Test] Write failing notification deep-link component/browser tests in `frontend/tests/component/schedule-notifications.test.tsx` and `frontend/tests/e2e/collaboration-notifications.spec.ts`; self-check: reminder opens the authorized date/item or source and missing/denied targets disclose no content (AC: AC-005, AC-009)

### Implementation

- [x] T081 [US5] [Backend] Implement bounded due-occurrence scanning, temporal-grant revalidation, and per-channel dispatch claims in `backend/apps/schedules/reminder_services.py`; self-check: T077 passes and each batch remains bounded/idempotent (AC: AC-003, AC-005, AC-007)
- [x] T082 [US5] [Backend] Integrate schedule delivery policies with existing Notification creation/status/retry in `backend/apps/notifications/services.py`; self-check: `in_app_only` is terminal and email worker selects only `in_app_email` records (AC: AC-005)
- [x] T083 [US5] [Backend] Add schedule reminder Celery task and five-minute Beat registration in `backend/apps/notifications/tasks.py` and `backend/apps/notifications/management/commands/ensure_notification_schedule.py`; self-check: repeated registration is idempotent and T078 passes in eager mode (AC: AC-005; Gate: Operations)
- [x] T084 [US5] [Backend] Extend notification serializer/list behavior for schedule event fields in `backend/apps/notifications/serializers.py` and `backend/apps/notifications/views.py`; self-check: T079 passes and notification visibility repeats schedule/source authorization (AC: AC-005, AC-009)
- [x] T085 [P] [US5] [Frontend] Add schedule notification labels, channel status, and dashboard/source deep-link handling in `frontend/src/features/notifications/NotificationList.tsx`; self-check: one top entry renders per schedule event and email status does not duplicate it (AC: AC-005)
- [x] T086 [P] [US5] [Ops] Add privacy-safe reminder lag, claimed/created/skipped/failed, retry, and per-channel counters to `backend/apps/common/views.py` and schedule task logging; self-check: metrics distinguish in-app/email failures without titles, descriptions, recipient emails, or reminder content (AC: AC-005, AC-009; Gate: Observability)
- [x] T087 [US5] [Validation] Run and document US5 checkpoint results in `specs/015-dashboard-calendar/quickstart.md`; self-check: eligibility, deduplication, email retry, skip, notification list, and deep-link tests pass independently (AC: AC-005, AC-009)

**Checkpoint**: US5 reminders meet timing, idempotency, privacy, degradation, and
navigation expectations using the existing worker/Beat topology.

---

## Phase 8: Polish and Cross-Cutting Release Gates

**Purpose**: Validate the complete feature against security, performance,
accessibility, migration, operations, documentation, and CI requirements.

- [x] T088 [P] [Test] Add full role/privacy matrix for calendar, private detail, conflict, cursor, audience, revision, delivery, notification, and direct-ID paths in `backend/tests/integration/test_schedule_security_matrix.py`; self-check: zero private-content or unrelated-account disclosure occurs (AC: AC-001, AC-003, AC-009)
- [x] T089 [P] [Test] Add XSS-safe schedule text and action-path authorization cases in `backend/tests/integration/test_schedule_security_matrix.py` and `frontend/tests/component/dashboard-calendar.test.tsx`; self-check: content renders as text and stale/forged paths expose no source data (AC: AC-009; Gate: Security)
- [x] T090 [P] [Frontend] Complete responsive calendar/detail/form CSS and visual states in `frontend/src/styles/globals.css`; self-check: Playwright overlap/overflow checks pass at 390, 900, and 1440 CSS px with long localized titles (AC: AC-006)
- [x] T091 [P] [Test] Extend keyboard, semantics, color-independence, focus, live-region, and dialog accessibility coverage in `frontend/tests/e2e/accessibility.spec.ts`; self-check: automated checks and keyboard journeys pass for all calendar views/forms (AC: AC-006, AC-010)
- [x] T092 [Test] Run production UI screenshot/overlap validation and add dashboard calendar assertions in `frontend/tests/e2e/production-ui.spec.ts`; self-check: zero clipped primary actions, horizontal overflow, or visible text overlap at supported widths (AC: AC-006)
- [x] T093 [P] [Test] Finalize production-shaped occurrence/audience/reminder query-count and p95 validation in `backend/tests/integration/test_calendar_performance.py`; self-check: 500 accounts, 10,000 occurrences, 500 recipients, and five-minute eligibility targets pass (AC: AC-005, AC-007)
- [x] T094 [P] [Ops] Add schedule migration/Beat/readiness/rollback assertions to `backend/tests/integration/test_production_readiness.py` and `scripts/check-production-readiness.sh`; self-check: schema-first deployment and application-first rollback preserve existing workflows (AC: AC-011, AC-012; Gate: Operations)
- [x] T095 [P] [Docs] Synchronize implemented schema/UI differences in `specs/015-dashboard-calendar/contracts/openapi.yaml`, `contracts/frontend-ui.md`, `data-model.md`, and `quickstart.md`; self-check: generated OpenAPI and documented role/channel/report behavior have no drift (Gate: Documentation)
- [x] T096 [P] [Docs] Update local dependency, migration, worker/Beat, test, and rollback commands in `README.md` and `docs/production.md`; self-check: commands run in the documented environment and no new secret/service is claimed (Gate: Documentation)
- [x] T097 [CI] Run backend ruff, full pytest, migration dry-run, OpenAPI check, frontend lint/test/build, fullstack Playwright schedule suites, generated-artifact guard, and production-readiness scripts from `.github/workflows/release.yml`; self-check: every CI-equivalent command exits zero and no generated artifacts remain (Gate: CI/CD)
- [ ] T098 [Review] Record Product, Testing, and Development acceptance or a governed release exception in `specs/015-dashboard-calendar/spec.md`; self-check: production release is not approved while any required review remains Pending (Gate: Review Readiness)

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies.
- **Phase 2 Foundational**: depends on Phase 1 and blocks all stories.
- **US1**: depends on Phase 2 and is the MVP.
- **US2**: depends on Phase 2; may run alongside US1 after shared serializers,
  permissions, and occurrence expansion are stable.
- **US3**: depends on Phase 2; uses authored schedule mutation from US2 for the
  optional private-to-group publish path, but direct group creation remains
  independently testable.
- **US4**: depends on US3 publication/audience/grant behavior.
- **US5**: depends on US3 publication and US4 cancellation/dynamic grant behavior.
- **Phase 8**: depends on every story selected for release.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 (MVP)
                    -> US2 -> US3 -> US4 -> US5
                       \------> US3 (direct group create path)
US1 + US2 + US3 + US4 + US5 -> Polish/Release Gates
```

### Within Each Story

- Complete all story test tasks and confirm they fail before implementation.
- Implement models/shared foundations before services, services before endpoints,
  endpoints before UI integration, and integration before checkpoint validation.
- Do not mark a task complete until its stated self-check passes.
- Stop at each checkpoint; do not conceal a failing earlier story with later
  implementation.

## Parallel Opportunities

### Setup and Foundation

- T001-T005 can run in parallel because they touch separate dependency/module/
  fixture paths.
- T006-T009 can run in parallel as failing tests.
- After T010-T014 establish models/migrations, T015-T020 can be divided across
  recurrence, permissions, audit, frontend contract, and event-cursor owners.

### User Story 1

```text
Parallel tests: T021, T022, T023, T024, T025, T026
Parallel adapters after tests: T027, T028, T029
Parallel frontend surfaces after API shape: T034, T035
Join points: T032 -> T033 -> T036/T037
```

### User Story 2

```text
Parallel tests: T038, T039, T040, T041, T042
Parallel implementation after T043: T044, T046, T047
Join points: T045 -> T048 -> T049
```

### User Story 3

```text
Parallel tests: T050, T051, T052, T053, T054
Backend sequence: T055 -> T056 -> T057/T058 -> T059
Parallel frontend after contract: T060, T061
Join points: T062/T063 -> T064
```

### User Story 4

```text
Parallel tests: T065, T066, T067, T068
Backend sequence: T069/T070 -> T071/T072 -> T073
Parallel frontend after contract: T074, T075
Join point: T076
```

### User Story 5

```text
Parallel tests: T077, T078, T079, T080
Backend sequence: T081 -> T082 -> T083 -> T084
Parallel UI/operations after contract: T085, T086
Join point: T087
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 only.
3. Stop and validate unified authorized calendar, source projections, project
   weekly report policy, performance, and responsive layout.
4. Demonstrate/deploy behind the existing authenticated dashboard only after the
   US1 checkpoint passes.

### Incremental Delivery

1. **US1**: read-only unified calendar and project report scheduling.
2. **US2**: owner-only personal planning.
3. **US3**: role-bounded group publication with in-app-only publication notices.
4. **US4**: recurrence changes, dynamic membership, history, and cancellation.
5. **US5**: due reminders and channel-aware email delivery.
6. Complete cross-cutting release gates after all desired stories pass.

### Parallel Team Strategy

- Backend foundation owners handle schema/recurrence/authorization while frontend
  owners prepare public API types and failing component tests.
- After Foundation, US1 projection/report work and US2 private-mutation work can
  proceed in parallel.
- US3 audience/search UI can begin from the contract while backend audience
  services are implemented, but integration waits for T059.
- Security, accessibility, performance, and operations owners can prepare Phase
  8 tests early; they run as release gates only after story completion.

## Notes

- `[P]` means different files or a safe independent test surface; same-file join
  points are intentionally serial.
- Every user-story task carries `[US1]` through `[US5]`; Setup, Foundational, and
  Polish tasks intentionally have no story label.
- All business tests precede their paired implementation task and must fail first.
- `specs/` is currently ignored by `.gitignore`; ensure the governed PR process
  includes `spec.md`, plan artifacts, and this `tasks.md` as required by the
  constitution.
- Recommended commit format: `[015] 描述变更内容`.

## UI Refinement Follow-up

- [X] T099 [P] [US1] [Frontend] Refine the dashboard calendar hierarchy with a compact source menu, bounded month cells, grouped agenda rows, contextual upcoming/detail sidebar, and compact mobile representation in `frontend/src/features/schedules/CalendarToolbar.tsx`, `CalendarGrid.tsx`, `CalendarAgenda.tsx`, `ScheduleDetailPanel.tsx`, `frontend/src/app/HomePage.tsx`, and `frontend/src/styles/globals.css`; self-check: 390, 900, and 1440 CSS px remain free of horizontal overflow and visible text overlap (AC: AC-002, AC-006; UX: UX-007)
