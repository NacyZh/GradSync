# Tasks: Research Group Operations

**Input**: Design documents from `/specs/001-research-group-ops/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Automated tests are required by the GradSync constitution and plan. Each user story includes contract, integration, frontend, and end-to-end coverage before implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation. User Story 1 is the MVP because it establishes project membership, project-scoped records, task hierarchy, and deadline notifications.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks in the same phase
- **[Story]**: User story label from spec.md, required only inside story phases
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Django backend, React/Vite frontend, Docker Compose services, and shared toolchain.

- [X] T001 Create backend and frontend directory skeletons in backend/manage.py, backend/gradsync/__init__.py, backend/apps/__init__.py, frontend/package.json, frontend/src/app/App.tsx, docker/backend.Dockerfile, docker/frontend.Dockerfile
- [X] T002 Configure backend project metadata and dependencies in backend/pyproject.toml
- [X] T003 Configure Django project settings modules in backend/gradsync/settings/base.py, backend/gradsync/settings/local.py, backend/gradsync/settings/test.py, backend/gradsync/urls.py, backend/gradsync/asgi.py
- [X] T004 Configure Celery application entrypoint in backend/gradsync/celery.py
- [X] T005 Configure frontend TypeScript, Vite, and package scripts in frontend/tsconfig.json, frontend/vite.config.ts, frontend/package.json
- [X] T006 [P] Configure frontend linting and formatting in frontend/eslint.config.js, frontend/prettier.config.js
- [X] T007 [P] Configure backend linting, formatting, and pytest defaults in backend/pyproject.toml, backend/pytest.ini
- [X] T008 Configure Docker Compose services for backend, frontend, PostgreSQL, Redis, worker, scheduler, and email sink in docker-compose.yml
- [X] T009 [P] Add environment variable templates for local services in .env.example
- [X] T010 [P] Create backend test package structure in backend/tests/unit/__init__.py, backend/tests/integration/__init__.py, backend/tests/contract/__init__.py, backend/tests/conftest.py
- [X] T011 [P] Create frontend test package structure in frontend/src/test/setup.ts, frontend/tests/e2e/.gitkeep, frontend/tests/component/.gitkeep
- [X] T012 [P] Add OpenAPI contract copy/check script in scripts/check-openapi-contract.sh

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish authentication, app scaffolding, shared API behavior, background jobs, and test utilities required by every story.

**Critical**: No user story implementation starts until this phase is complete.

- [X] T013 Create Django app packages and app configs in backend/apps/accounts/apps.py, backend/apps/projects/apps.py, backend/apps/tasks/apps.py, backend/apps/submissions/apps.py, backend/apps/resources/apps.py, backend/apps/notifications/apps.py, backend/apps/audit/apps.py
- [X] T014 Implement custom user model and manager in backend/apps/accounts/models.py, backend/apps/accounts/managers.py
- [X] T015 [P] Implement user admin registration in backend/apps/accounts/admin.py
- [X] T016 Implement account serializers and current-user endpoint in backend/apps/accounts/serializers.py, backend/apps/accounts/views.py, backend/apps/accounts/urls.py
- [X] T017 Implement shared DRF response, pagination, and exception handling in backend/apps/common/api.py, backend/apps/common/exceptions.py, backend/apps/common/pagination.py
- [X] T018 Implement shared project membership permission helpers in backend/apps/common/permissions.py
- [X] T019 Implement project-scoped queryset mixins and service base classes in backend/apps/common/project_scope.py
- [X] T020 Implement audit event model and append-only service in backend/apps/audit/models.py, backend/apps/audit/services.py
- [X] T021 [P] Implement backend factories for users and shared test helpers in backend/tests/factories/accounts.py, backend/tests/helpers.py
- [X] T022 [P] Implement frontend API client, error normalization, and query provider in frontend/src/shared/api/client.ts, frontend/src/shared/api/errors.ts, frontend/src/app/queryClient.tsx
- [X] T023 [P] Implement frontend auth context and protected route shell in frontend/src/features/auth/AuthProvider.tsx, frontend/src/routes/ProtectedRoute.tsx
- [X] T024 [P] Implement shared UI states for loading, empty, error, and confirmation in frontend/src/shared/ui/AsyncState.tsx, frontend/src/shared/ui/FormStatus.tsx
- [X] T025 Configure Celery worker, scheduler, and email backend settings in backend/gradsync/settings/base.py, backend/apps/notifications/celery.py
- [X] T026 Create initial database migration package placeholders in backend/apps/accounts/migrations/__init__.py, backend/apps/projects/migrations/__init__.py, backend/apps/tasks/migrations/__init__.py, backend/apps/submissions/migrations/__init__.py, backend/apps/resources/migrations/__init__.py, backend/apps/notifications/migrations/__init__.py, backend/apps/audit/migrations/__init__.py
- [X] T027 [P] Implement seed command for advisor/student/resource demo data in backend/apps/accounts/management/commands/seed_demo_research_ops.py
- [X] T028 [P] Add frontend route registry and application layout shell in frontend/src/routes/index.tsx, frontend/src/app/App.tsx, frontend/src/app/Layout.tsx

**Checkpoint**: Backend, frontend, containers, auth shell, shared permissions, audit support, and test utilities are ready.

---

## Phase 3: User Story 1 - Manage Project Work (Priority: P1) MVP

**Goal**: Advisors create projects, assign students, define hierarchical tasks and deadlines, and users only see records for projects where they are members.

**Independent Test**: Create two projects with different memberships, add parent and child tasks with deadlines, and verify each participant only sees and updates records for their own projects.

### Tests for User Story 1

- [X] T029 [P] [US1] Add contract tests for project list/create/dashboard/member endpoints in backend/tests/contract/test_projects_api.py
- [X] T030 [P] [US1] Add contract tests for task list/create/update endpoints in backend/tests/contract/test_tasks_api.py
- [X] T031 [P] [US1] Add unit tests for project membership and role rules in backend/tests/unit/test_project_membership_rules.py
- [X] T032 [P] [US1] Add unit tests for task hierarchy, deadline, and cycle validation in backend/tests/unit/test_task_hierarchy_rules.py
- [X] T033 [P] [US1] Add integration tests for cross-project isolation across projects, tasks, audit events, and notifications in backend/tests/integration/test_project_isolation.py
- [X] T034 [P] [US1] Add integration tests for deadline notification eligibility in backend/tests/integration/test_deadline_notifications.py
- [X] T035 [P] [US1] Add frontend component tests for project selector, task tree, and project dashboard states in frontend/tests/component/project-work.test.tsx
- [X] T036 [P] [US1] Add Playwright MVP flow for advisor project setup and student project isolation in frontend/tests/e2e/project-work.spec.ts

### Implementation for User Story 1

- [X] T037 [P] [US1] Implement ResearchProject and ProjectMembership models in backend/apps/projects/models.py
- [X] T038 [P] [US1] Implement Task model with parent, assignee, status, priority, deadline, and same-project fields in backend/apps/tasks/models.py
- [X] T039 [US1] Create migrations for project membership and task hierarchy in backend/apps/projects/migrations/0001_initial.py, backend/apps/tasks/migrations/0001_initial.py
- [X] T040 [US1] Implement project membership service and project-scoped access helpers in backend/apps/projects/services.py
- [X] T041 [US1] Implement task hierarchy validation and task status service in backend/apps/tasks/services.py
- [X] T042 [US1] Implement project serializers and viewsets for list, create, dashboard, and members in backend/apps/projects/serializers.py, backend/apps/projects/views.py
- [X] T043 [US1] Implement task serializers and viewsets for list, create, update, and hierarchy rendering in backend/apps/tasks/serializers.py, backend/apps/tasks/views.py
- [X] T044 [US1] Wire project and task routes in backend/apps/projects/urls.py, backend/apps/tasks/urls.py, backend/gradsync/urls.py
- [X] T045 [US1] Implement deadline reminder notification records and Celery tasks in backend/apps/notifications/models.py, backend/apps/notifications/tasks.py
- [X] T046 [US1] Implement audit logging for project creation, membership changes, task creation, and task status changes in backend/apps/audit/services.py
- [X] T047 [US1] Implement typed project and task API functions in frontend/src/features/projects/api.ts, frontend/src/features/tasks/api.ts
- [X] T048 [US1] Implement project selector and visible project context header in frontend/src/features/projects/ProjectSelector.tsx, frontend/src/app/Layout.tsx
- [X] T049 [US1] Implement advisor project creation and membership management views in frontend/src/features/projects/ProjectCreatePage.tsx, frontend/src/features/projects/ProjectMembersPanel.tsx
- [X] T050 [US1] Implement project dashboard with tasks, pending reviews placeholder, bookings placeholder, and activity feed in frontend/src/features/projects/ProjectDashboardPage.tsx
- [X] T051 [US1] Implement task tree, task creation form, and task status controls in frontend/src/features/tasks/TaskTree.tsx, frontend/src/features/tasks/TaskForm.tsx, frontend/src/features/tasks/TaskStatusControl.tsx
- [X] T052 [US1] Add accessible loading, empty, success, warning, and error states to project and task workflows in frontend/src/features/projects/ProjectStates.tsx, frontend/src/features/tasks/TaskStates.tsx
- [X] T053 [US1] Add project/task routes to frontend route registry in frontend/src/routes/index.tsx
- [X] T054 [US1] Implement project isolation and dashboard seed data for quickstart validation in backend/apps/projects/management/commands/seed_demo_research_ops.py
- [X] T055 [US1] Validate project dashboard and task search performance with 500 active records in backend/tests/integration/test_project_performance.py

**Checkpoint**: User Story 1 is independently functional and demonstrable as the MVP.

---

## Phase 4: User Story 2 - Review Drafts and Progress Reports (Priority: P2)

**Goal**: Students submit versioned paper drafts and weekly reports under a project; advisors add inline comments and update review status without comments drifting across versions.

**Independent Test**: Submit multiple draft versions and weekly reports, add advisor comments to specific anchors, and verify version history, comment placement, review status, project isolation, and notification records.

### Tests for User Story 2

- [X] T056 [P] [US2] Add contract tests for draft family and draft version endpoints in backend/tests/contract/test_drafts_api.py
- [X] T057 [P] [US2] Add contract tests for weekly report and inline comment endpoints in backend/tests/contract/test_reports_comments_api.py
- [X] T058 [P] [US2] Add unit tests for draft version immutability and version numbering in backend/tests/unit/test_draft_version_rules.py
- [X] T059 [P] [US2] Add unit tests for weekly report uniqueness and review state transitions in backend/tests/unit/test_weekly_report_rules.py
- [X] T060 [P] [US2] Add unit tests for inline comment same-project target validation in backend/tests/unit/test_inline_comment_rules.py
- [X] T061 [P] [US2] Add integration tests for draft/report submission notifications and pending-review reminders in backend/tests/integration/test_review_notifications.py
- [X] T062 [P] [US2] Add frontend component tests for draft version list, report form, review queue, and inline comment states in frontend/tests/component/submission-review.test.tsx
- [X] T063 [P] [US2] Add Playwright flow for student submissions and advisor inline review in frontend/tests/e2e/submission-review.spec.ts

### Implementation for User Story 2

- [X] T064 [P] [US2] Implement Draft and DraftVersion models in backend/apps/submissions/models.py
- [X] T065 [P] [US2] Implement WeeklyProgressReport and InlineComment models in backend/apps/submissions/models.py
- [X] T066 [US2] Create migrations for drafts, draft versions, weekly reports, and inline comments in backend/apps/submissions/migrations/0001_initial.py
- [X] T067 [US2] Implement draft versioning service with immutable version review targets in backend/apps/submissions/draft_services.py
- [X] T068 [US2] Implement weekly report service with one active report per student/project/week in backend/apps/submissions/report_services.py
- [X] T069 [US2] Implement inline comment service with same-project target and anchor validation in backend/apps/submissions/comment_services.py
- [X] T070 [US2] Implement draft, report, and comment serializers in backend/apps/submissions/serializers.py
- [X] T071 [US2] Implement draft, report, and comment viewsets matching contracts in backend/apps/submissions/views.py
- [X] T072 [US2] Wire submission and comment routes in backend/apps/submissions/urls.py, backend/gradsync/urls.py
- [X] T073 [US2] Implement new-submission and pending-review notification tasks in backend/apps/notifications/tasks.py
- [X] T074 [US2] Implement audit logging for draft submission, report submission, inline comments, and review status changes in backend/apps/audit/services.py
- [X] T075 [US2] Implement typed draft, report, and comment API functions in frontend/src/features/submissions/api.ts
- [X] T076 [US2] Implement student draft submission and version history views in frontend/src/features/submissions/DraftSubmissionPage.tsx, frontend/src/features/submissions/DraftVersionHistory.tsx
- [X] T077 [US2] Implement weekly progress report form and history view in frontend/src/features/submissions/WeeklyReportPage.tsx, frontend/src/features/submissions/WeeklyReportHistory.tsx
- [X] T078 [US2] Implement advisor review queue and inline comment panel in frontend/src/features/submissions/ReviewQueuePage.tsx, frontend/src/features/submissions/InlineCommentPanel.tsx
- [X] T079 [US2] Implement review status controls and comment resolution UI in frontend/src/features/submissions/ReviewStatusControl.tsx, frontend/src/features/submissions/CommentThread.tsx
- [X] T080 [US2] Add submission and review routes to frontend route registry in frontend/src/routes/index.tsx
- [X] T081 [US2] Extend project dashboard pending review cards with real draft/report data in frontend/src/features/projects/ProjectDashboardPage.tsx
- [X] T082 [US2] Validate draft/report search and update confirmation performance in backend/tests/integration/test_submission_performance.py

**Checkpoint**: User Stories 1 and 2 are independently functional and can be demonstrated together.

---

## Phase 5: User Story 3 - Reserve Lab Resources (Priority: P3)

**Goal**: Project members reserve lab equipment or seats without overlap, see bookings only in authorized project contexts, and receive booking notifications.

**Independent Test**: Create resources and bookings for authorized project members, reject overlapping reservations, confirm non-overlapping reservations succeed, and verify booking visibility and notifications remain project-scoped.

### Tests for User Story 3

- [X] T083 [P] [US3] Add contract tests for lab resource and booking endpoints in backend/tests/contract/test_resources_bookings_api.py
- [X] T084 [P] [US3] Add unit tests for booking time-window validation and resource status rules in backend/tests/unit/test_booking_rules.py
- [X] T085 [P] [US3] Add integration tests for concurrent overlapping booking prevention in backend/tests/integration/test_booking_conflicts.py
- [X] T086 [P] [US3] Add integration tests for project-scoped booking visibility and booking notifications in backend/tests/integration/test_booking_project_scope.py
- [X] T087 [P] [US3] Add frontend component tests for resource list, booking form, conflict message, and booking states in frontend/tests/component/resource-booking.test.tsx
- [X] T088 [P] [US3] Add Playwright flow for resource booking conflict and non-overlap success in frontend/tests/e2e/resource-booking.spec.ts

### Implementation for User Story 3

- [X] T089 [P] [US3] Implement LabResource and Booking models in backend/apps/resources/models.py
- [X] T090 [US3] Create migrations for lab resources and bookings in backend/apps/resources/migrations/0001_initial.py
- [X] T091 [US3] Implement booking conflict detection with transaction-safe validation in backend/apps/resources/services.py
- [X] T092 [US3] Implement lab resource and booking serializers in backend/apps/resources/serializers.py
- [X] T093 [US3] Implement lab resource list and project booking viewsets matching contracts in backend/apps/resources/views.py
- [X] T094 [US3] Wire resource and booking routes in backend/apps/resources/urls.py, backend/gradsync/urls.py
- [X] T095 [US3] Implement booking change notification tasks and delivery records in backend/apps/notifications/tasks.py, backend/apps/notifications/models.py
- [X] T096 [US3] Implement audit logging for booking create, change, cancel, and completion events in backend/apps/audit/services.py
- [X] T097 [US3] Implement typed resource and booking API functions in frontend/src/features/resources/api.ts
- [X] T098 [US3] Implement resource availability list and booking calendar view in frontend/src/features/resources/ResourceListPage.tsx, frontend/src/features/resources/BookingCalendar.tsx
- [X] T099 [US3] Implement booking form, conflict feedback, cancel action, and confirmation states in frontend/src/features/resources/BookingForm.tsx, frontend/src/features/resources/BookingConflictAlert.tsx, frontend/src/features/resources/BookingActions.tsx
- [X] T100 [US3] Add booking routes and dashboard booking cards to frontend/src/routes/index.tsx, frontend/src/features/projects/ProjectDashboardPage.tsx
- [X] T101 [US3] Validate booking search and update confirmation performance in backend/tests/integration/test_booking_performance.py

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish documentation, security, accessibility, performance, and release validation across all stories.

- [X] T102 [P] Add backend OpenAPI schema generation and contract drift check in backend/apps/common/schema.py, scripts/check-openapi-contract.sh
- [X] T103 [P] Add frontend accessibility checks for project context, forms, comments, and booking controls in frontend/tests/e2e/accessibility.spec.ts
- [X] T104 [P] Add notification delivery status admin and project-scoped list coverage in backend/apps/notifications/admin.py, frontend/src/features/notifications/NotificationList.tsx
- [X] T105 Add archived-project read-only enforcement across tasks, submissions, comments, bookings, and notifications in backend/apps/projects/archive_services.py
- [X] T106 Add end-to-end archived project validation from quickstart in frontend/tests/e2e/archived-project.spec.ts
- [X] T107 [P] Document local Docker Compose setup and validation scenarios in README.md
- [X] T108 [P] Add performance seed command for 50 projects and 500 active records in backend/apps/projects/management/commands/seed_performance_research_ops.py
- [X] T109 Run full quickstart validation and record outcomes in specs/001-research-group-ops/quickstart-results.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1.
- **Phase 3 User Story 1**: Depends on Phase 2 and is the MVP.
- **Phase 4 User Story 2**: Depends on Phase 3 because drafts, reports, and comments require project membership and project context.
- **Phase 5 User Story 3**: Depends on Phase 3 because bookings require project membership and project context; it can run in parallel with Phase 4 after US1 is complete if backend project-scope helpers are stable.
- **Phase 6 Polish**: Depends on completed desired user stories.

### User Story Dependencies

- **US1 Manage Project Work**: Required first; establishes project isolation, membership, task hierarchy, and deadline reminders.
- **US2 Review Drafts and Progress Reports**: Requires US1 project membership and project dashboard routes.
- **US3 Reserve Lab Resources**: Requires US1 project membership and project dashboard routes; independent of US2 once US1 is complete.

### Within Each User Story

- Contract, unit, integration, component, and end-to-end tests are written first and should fail before implementation.
- Models and migrations precede services.
- Services precede serializers and viewsets.
- Backend routes precede frontend API calls.
- Frontend API calls precede views and route integration.
- Story performance validation runs after the story workflow is functional.

## Parallel Opportunities

- Setup tasks T006, T007, T009, T010, T011, and T012 can run in parallel after T001.
- Foundational tasks T015, T021, T022, T023, T024, T027, and T028 can run in parallel after T013.
- US1 test tasks T029 through T036 can run in parallel.
- US2 test tasks T056 through T063 can run in parallel.
- US3 test tasks T083 through T088 can run in parallel.
- US2 and US3 can proceed in parallel after US1 if separate developers own submissions and resources.

## Parallel Examples

### User Story 1

```bash
Task: "T029 [P] [US1] Add contract tests for project list/create/dashboard/member endpoints in backend/tests/contract/test_projects_api.py"
Task: "T030 [P] [US1] Add contract tests for task list/create/update endpoints in backend/tests/contract/test_tasks_api.py"
Task: "T035 [P] [US1] Add frontend component tests for project selector, task tree, and project dashboard states in frontend/tests/component/project-work.test.tsx"
Task: "T036 [P] [US1] Add Playwright MVP flow for advisor project setup and student project isolation in frontend/tests/e2e/project-work.spec.ts"
```

### User Story 2

```bash
Task: "T056 [P] [US2] Add contract tests for draft family and draft version endpoints in backend/tests/contract/test_drafts_api.py"
Task: "T057 [P] [US2] Add contract tests for weekly report and inline comment endpoints in backend/tests/contract/test_reports_comments_api.py"
Task: "T062 [P] [US2] Add frontend component tests for draft version list, report form, review queue, and inline comment states in frontend/tests/component/submission-review.test.tsx"
Task: "T063 [P] [US2] Add Playwright flow for student submissions and advisor inline review in frontend/tests/e2e/submission-review.spec.ts"
```

### User Story 3

```bash
Task: "T083 [P] [US3] Add contract tests for lab resource and booking endpoints in backend/tests/contract/test_resources_bookings_api.py"
Task: "T084 [P] [US3] Add unit tests for booking time-window validation and resource status rules in backend/tests/unit/test_booking_rules.py"
Task: "T087 [P] [US3] Add frontend component tests for resource list, booking form, conflict message, and booking states in frontend/tests/component/resource-booking.test.tsx"
Task: "T088 [P] [US3] Add Playwright flow for resource booking conflict and non-overlap success in frontend/tests/e2e/resource-booking.spec.ts"
```

## Phase 7: Convergence

- [X] T110 CRITICAL: Replace shell-only frontend e2e/component tests with workflow assertions for project setup/isolation, submissions/review, bookings, archived read-only behavior, and accessibility states per Constitution II / plan: Testing
- [X] T111 Implement advisor-only project update, archive, reopen, and membership management endpoints with matching frontend controls per FR-001, FR-016
- [X] T112 Enforce task creation/update role rules, task status transition rules, and audit-visible status history for advisor and assignee actions per FR-003, FR-005, FR-018
- [X] T113 Populate project dashboard and activity views with project-scoped current tasks, pending draft/report reviews, upcoming bookings, comments, notifications, and audit events per FR-010
- [X] T114 Enforce student-only draft/report submission ownership and wire frontend draft submission, version history, weekly report form, and report history to backend APIs per FR-006, FR-008, FR-016
- [X] T115 Add advisor review status APIs and connected review queue/status controls for draft versions and weekly progress reports per FR-009, US2/AC3
- [X] T116 Complete inline comment listing, anchoring display, resolution, and connected frontend comment thread behavior for draft versions and weekly reports per FR-007, FR-009
- [X] T117 Implement future booking modification and cancellation policy with conflict validation, audit records, booking-change notifications, and connected frontend actions per FR-011, US3/AC3
- [X] T118 Implement project-scoped notification listing API, email queue/send processing, required email metadata/action paths, and delivery-status frontend display per FR-013, FR-014, FR-015
- [X] T119 Apply archived-project read-only guards across task, submission, comment, booking, and reminder services, including reopen behavior per FR-017
- [X] T120 Normalize user-friendly API validation errors and connect frontend loading, success, warning, empty, and error states for project, task, submission, comment, booking, and notification workflows per FR-020, UX-003
- [X] T121 Add measurable performance assertions and seeded scale validation for dashboard load, project-scoped search/filter, update confirmation, and reminder timing per PERF-001..PERF-005 / Constitution IV

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 for User Story 1.
3. Stop and validate project isolation, project setup, task hierarchy, deadline reminders, and performance targets.
4. Demo advisor project creation and student project-scoped task visibility.

### Incremental Delivery

1. Add US1 as the releaseable MVP.
2. Add US2 for draft/report submission and advisor review.
3. Add US3 for lab resource booking.
4. Complete cross-cutting polish and quickstart validation.

### Quality Gates

- Every task that changes behavior must have corresponding automated test coverage from the same story phase.
- No story is complete until contract, integration, frontend, end-to-end, accessibility, and performance expectations for that story pass.
- Project isolation is a release blocker for every story.

## Phase 8: Convergence

- [X] T122 CRITICAL: Replace development runtime containers with production backend and frontend images using Gunicorn or equivalent WSGI serving, static frontend assets, non-root runtime users, and no dev/test tooling per Constitution I / plan: Target Platform
- [X] T123 Add a production Docker Compose topology with healthchecks, restart policies, internal-only PostgreSQL/Redis networking, persistent volumes, migration/static collection flow, and no source bind mounts per plan: Docker Compose orchestration
- [X] T124 Add production Django settings and environment validation for secret key, DEBUG=false, allowed hosts, CSRF trusted origins, secure cookies, HTTPS/proxy headers, HSTS, CORS/origin policy, and fail-fast unsafe defaults per Constitution I / plan: deployment constraints
- [X] T125 Add PostgreSQL production migration, readiness, backup, restore, retention, and release-runbook support per plan: Storage / Target Platform
- [X] T126 Harden notification delivery for production SMTP/provider configuration, Celery worker/scheduler readiness, retries, queue separation, and delivery observability per FR-013, FR-014 / plan: Celery
- [X] T127 Add observability primitives including health endpoints, structured logging, request IDs, metrics, error reporting hooks, and alerting guidance per Constitution IV / Performance Goals
- [X] T128 Add CI/CD release pipeline for backend tests, frontend tests/build, Docker builds, migration checks, dependency audit, image scan, and deploy gating per Constitution II / Quality Gates
- [X] T129 Add production secret management artifacts including `.env.production.example`, secret rotation guidance, and removal of dev-default production assumptions per Constitution I / security quality
- [X] T130 Add production-readiness automated checks for secure settings, fresh database migrations, static asset delivery, container healthchecks, and SMTP delivery path per Constitution II / Testing
- [X] T131 Add production frontend serving and reverse-proxy strategy with Vite static build delivery, cache headers, API routing, and environment-specific API origin handling per plan: frontend web app
- [X] T132 Add production deployment, rollback, incident response, backup/restore, dependency vulnerability remediation, and release checklist documentation per Constitution I / Governance

## Phase 9: Convergence

- [X] T133 CRITICAL: Replace reachability-only Playwright checks with real advisor/student workflow assertions for project setup and isolation, draft/report submission and review, booking conflict handling, archived read-only behavior, and accessibility states per Constitution II / plan: Testing
- [X] T134 CRITICAL: Implement generated OpenAPI schema drift checking against specs/001-research-group-ops/contracts/openapi.yaml instead of file-presence-only validation per Constitution II / plan: contracts
- [X] T135 Implement scheduled reminder coverage for approaching project deadlines, task 7-day and 1-day deadline windows, pending reviews, and Celery Beat periodic execution per FR-013 / PERF-004
- [X] T136 Add project-scoped search and filter APIs plus measurable tests for tasks, drafts, weekly reports, inline comments, and bookings per PERF-002 / plan: Performance Goals
- [X] T137 Include inline comments and notification delivery events in project dashboard/activity timeline responses and frontend rendering per FR-010
- [X] T138 Add visible selected-project context to draft submission, weekly report, review queue, resource booking, and other project-scoped screens before create/submit/comment/book actions per FR-019 / UX-001
- [X] T139 Expand demo seeding to create quickstart-ready projects, memberships, hierarchical tasks, draft/report review data, lab resources, bookings, notifications, and activity records per T027 / T054 / quickstart
- [X] T140 Implement resource availability and booking calendar behavior with time-window availability data instead of an empty calendar shell per FR-011 / US3/AC1
- [X] T141 Add production error-reporting hook integration and an automated SMTP delivery-path probe in production readiness checks per T127 / T130
- [X] T142 Wire ProtectedRoute into project-scoped frontend routes so authenticated role-aware workflows are guarded at the router layer per FR-016 / plan: auth shell

## Phase 10: Convergence

- [X] T143 Document production environment secrets and credential inventory, including owners, storage location, rotation procedure, and readiness validation for Django, database, Redis, SMTP/provider, error reporting, registry, deploy, and backup credentials in docs/ops/credential-inventory.md, docs/ops/cicd-credentials.md, and scripts/check-production-readiness.sh per plan: deployment constraints / T129
- [X] T144 Define production infrastructure provisioning and acceptance checks for host capacity, networking, firewall rules, persistent volumes, database/Redis storage, scheduler/worker placement, and operational access in docs/ops/infrastructure.md and docker-compose.prod.yml per plan: Target Platform / T123
- [X] T145 Add TLS certificate, public domain, HTTPS termination, HSTS, redirect, and DNS validation artifacts for the production frontend/API route in docs/ops/tls-domain.md, .env.production.example, and backend/gradsync/settings/production.py per plan: frontend web app / T131
- [X] T146 Publish backend and frontend release images to an approved registry with immutable tags, provenance metadata, pull credentials, and promotion/deploy gates in .github/workflows/release.yml and scripts/deploy-production.sh per T128 / plan: Docker Compose orchestration
- [X] T147 Configure production monitoring alert routes and validation for healthchecks, 5xx rate, latency, database/Redis readiness, worker/scheduler absence, queue backlog, notification failures, and error-reporting events in docs/ops/monitoring-alerts.md, backend/apps/common/production_checks.py, and backend/tests/integration/test_production_readiness.py per Constitution IV / T127
- [X] T148 Complete production email provider setup with verified sender/domain authentication, provider credential landing, bounce/failure handling, rate-limit expectations, and a successful SMTP/provider probe in docs/ops/email-provider.md, backend/apps/common/management/commands/check_production_readiness.py, and backend/tests/integration/test_production_readiness.py per FR-013, FR-014 / T126
- [X] T149 Execute and document a backup restore drill with off-host encrypted backup storage, retention validation, RPO/RTO acceptance, and recovery evidence in docs/ops/backup-restore-drill.md, docs/ops/restore-drills/latest.md, scripts/postgres-backup.sh, scripts/postgres-restore.sh, and scripts/postgres-restore-drill.sh per plan: Storage / T125
- [X] T150 Document CI/CD deployment credentials in protected environments with secret validation, least-privilege registry/host access, manual approval gates, and rollback credential checks in docs/ops/cicd-credentials.md and .github/workflows/release.yml per T128 / Constitution II

## Phase 11: Convergence

- [X] T151 Implement a responsive role-aware frontend workspace shell with sidebar/topbar navigation, advisor/student/admin primary actions, notification entry point, project workflow links, and tablet/desktop layout coverage in frontend/src/app/Layout.tsx, frontend/src/app/styles.css, frontend/src/routes/index.tsx, frontend/tests/component/role-navigation.test.tsx, and frontend/tests/e2e/role-workspaces.spec.ts per UX-002 / plan: User Experience (partial)
- [X] T152 Build a task-driven project workspace with expandable task tree or board, task detail panel, status controls, deadline/progress visualization, member summary, and dashboard integration in frontend/src/features/projects/ProjectDashboardPage.tsx, frontend/src/features/tasks/TaskTree.tsx, frontend/src/features/tasks/TaskForm.tsx, frontend/src/features/tasks/TaskStatusControl.tsx, frontend/tests/component/project-work.test.tsx, and frontend/tests/e2e/project-work.spec.ts per US1/AC2, FR-003, FR-005 (partial)
- [X] T153 Complete student submission and advisor review UX with draft version history selection, weekly report rich editing affordances, side-by-side review layout, anchored inline comment timeline, comment replies/resolution, review status controls, and role-specific task flows in frontend/src/features/submissions/DraftSubmissionPage.tsx, frontend/src/features/submissions/DraftVersionHistory.tsx, frontend/src/features/submissions/WeeklyReportPage.tsx, frontend/src/features/submissions/WeeklyReportHistory.tsx, frontend/src/features/submissions/ReviewQueuePage.tsx, frontend/src/features/submissions/InlineCommentPanel.tsx, frontend/src/features/submissions/CommentThread.tsx, frontend/tests/component/submission-review.test.tsx, and frontend/tests/e2e/submission-review.spec.ts per US2/AC1..AC3, FR-006..FR-009 (partial)
- [X] T154 Upgrade the project dashboard and notification UX with task-oriented KPI cards, recent activity timeline, pending todo list, notification center/dropdown, delivery-status details, unread/priority treatment, and project-scoped filtering in frontend/src/features/projects/ProjectDashboardPage.tsx, frontend/src/features/notifications/NotificationList.tsx, frontend/src/features/notifications/api.ts, frontend/tests/component/project-work.test.tsx, and frontend/tests/e2e/project-work.spec.ts per FR-010, FR-015, UX-003 (partial)
- [X] T155 Complete resource booking UX with searchable resource availability, booking cards/calendar states, conflict explanation panel, future booking modification/cancellation controls, destructive-action confirmation dialogs, and project-scoped booking notifications in frontend/src/features/resources/ResourceListPage.tsx, frontend/src/features/resources/BookingCalendar.tsx, frontend/src/features/resources/BookingForm.tsx, frontend/src/features/resources/BookingActions.tsx, frontend/src/features/resources/BookingConflictAlert.tsx, frontend/tests/component/resource-booking.test.tsx, and frontend/tests/e2e/resource-booking.spec.ts per US3/AC1..AC3, FR-011, FR-012, UX-003 (partial)
- [X] T156 Add shared frontend interaction feedback primitives for skeleton loading states, actionable empty states, toast success/error feedback, reusable confirmation dialogs, and Ctrl+S/Ctrl+Enter form shortcuts in frontend/src/shared/ui/AsyncState.tsx, frontend/src/shared/ui/FormStatus.tsx, frontend/src/app/App.tsx, frontend/src/app/styles.css, frontend/tests/component/project-work.test.tsx, frontend/tests/component/submission-review.test.tsx, and frontend/tests/e2e/accessibility.spec.ts per UX-003, UX-004, UX-005, Constitution III (partial)
- [X] T157 Add accessible light/dark theme support with CSS design tokens, persisted theme preference, theme toggle in the app shell, and contrast/focus validation in frontend/src/app/Layout.tsx, frontend/src/app/styles.css, frontend/src/test/setup.ts, frontend/tests/component/role-navigation.test.tsx, and frontend/tests/e2e/accessibility.spec.ts per plan: User Experience / Constitution III (missing)
- [X] T158 Expand frontend automated coverage for keyboard navigation, focus order, responsive desktop/tablet layouts, theme switching, skeleton states, toast feedback, confirmation dialogs, and role-specific workflow completion in frontend/tests/component/*.test.tsx and frontend/tests/e2e/*.spec.ts per plan: Testing / Constitution II (partial)
- [X] T159 Decide whether the requested paper library, code repository, Tailwind/shadcn, Redux Toolkit, PDF/DOI/BibTeX, and WebSocket capabilities belong in this feature or a separate feature, then update the appropriate Spec Kit artifacts before implementation in specs/001-research-group-ops/spec.md, specs/001-research-group-ops/plan.md, and specs/001-research-group-ops/tasks.md per user-requested frontend scope beyond current artifacts (unrequested)

## Phase 12: Convergence

- [X] T160 CRITICAL: Replace mocked frontend Playwright coverage with full-stack end-to-end flows that run against the real Django API, database-backed seed data, auth/session handling, and project-scoped records for project isolation, submissions/review, bookings, archived read-only behavior, and accessibility in frontend/tests/e2e/*.spec.ts, frontend/playwright.config.ts, docker-compose.yml, backend/apps/*/management/commands/*, and CI scripts per Constitution II / plan: Testing / T133 (contradicts)
- [X] T161 CRITICAL: Execute and document a real production-like restore drill, replace pending placeholder evidence in docs/ops/restore-drills/latest.md, and update backend/apps/common/production_checks.py plus backend/tests/integration/test_production_readiness.py so production readiness fails when restore evidence is missing, placeholder, stale, or lacks RPO/RTO validation per Constitution IV,V / plan: Storage / T149 (contradicts)
- [X] T162 Enforce future-only booking modification and cancellation by rejecting update_booking() and cancel_booking() when the reservation has started, then add backend tests and frontend validation/error feedback in backend/apps/resources/services.py, backend/tests/unit/test_booking_rules.py, backend/tests/integration/test_booking_project_scope.py, frontend/src/features/resources/BookingActions.tsx, frontend/src/features/resources/BookingForm.tsx, and frontend/tests/component/resource-booking.test.tsx per FR-011 / T117 (partial)
- [X] T163 Add project start/end date support and date-order validation to project creation, including backend serializer/service handling, API contract tests, frontend project creation fields, and user-friendly validation messages in backend/apps/projects/serializers.py, backend/apps/projects/services.py, backend/tests/contract/test_projects_api.py, frontend/src/features/projects/ProjectCreatePage.tsx, and frontend/tests/component/project-work.test.tsx per FR-001 (partial)
- [X] T164 Clean generated runtime/build artifacts from source scope and add ignore/release safeguards for Python __pycache__/.pyc, TypeScript .tsbuildinfo, generated Vite outputs, local frontend dist, and dependency caches so reviews and production images include only intentional source/build artifacts per Constitution I (unrequested)

## Phase 13: Convergence

**Purpose**: Replace the remaining demo-level frontend with a production-grade
Tailwind CSS and shadcn/ui architecture that satisfies
`contracts/frontend-ui.md`, preserves project isolation, and keeps every
advisor/student/admin workflow independently testable.

- [X] T165 CRITICAL: Add Tailwind CSS, shadcn/ui, Radix UI, class-variance-authority, and lucide-react setup in frontend/package.json, frontend/package-lock.json, frontend/tailwind.config.ts, frontend/postcss.config.js, frontend/components.json, frontend/vite.config.ts, and frontend/tsconfig.app.json
- [X] T166 CRITICAL: Replace ad hoc global styling with Tailwind layers, design tokens, theme variables, responsive density rules, and accessible focus states in frontend/src/app/styles.css
- [X] T167 [P] Add shadcn/ui base primitives for buttons, forms, overlays, navigation surfaces, feedback, and dense records in frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/textarea.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/alert-dialog.tsx, frontend/src/components/ui/dropdown-menu.tsx, frontend/src/components/ui/popover.tsx, frontend/src/components/ui/tabs.tsx, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/table.tsx, frontend/src/components/ui/toast.tsx, frontend/src/components/ui/skeleton.tsx, frontend/src/components/ui/alert.tsx, and frontend/src/components/ui/tooltip.tsx
- [X] T168 [P] Add GradSync shared UI adapters for page shell, project context, data states, confirmations, feedback, forms, status badges, and typed workspace composition in frontend/src/shared/ui/PageShell.tsx, frontend/src/shared/ui/ProjectContextBar.tsx, frontend/src/shared/ui/DataState.tsx, frontend/src/shared/ui/ConfirmDialog.tsx, frontend/src/shared/ui/FeedbackProvider.tsx, frontend/src/shared/ui/FormField.tsx, and frontend/src/shared/ui/StatusBadge.tsx
- [X] T169 [P] Add component tests for Tailwind/shadcn primitives, shared UI adapters, focus behavior, theme switching, toasts, skeletons, dialogs, tooltips, and live-region feedback in frontend/tests/component/design-system.test.tsx
- [X] T170 [P] Add component tests for the production workspace shell, role-aware navigation, project context visibility, responsive states, and route guards in frontend/tests/component/role-navigation.test.tsx
- [X] T171 Rebuild the authenticated app shell with Tailwind/shadcn layout regions, role-aware navigation, project context placement, theme toggle, notification entry point, and route composition in frontend/src/app/Layout.tsx, frontend/src/app/HomePage.tsx, frontend/src/app/App.tsx, and frontend/src/routes/index.tsx
- [X] T172 Rebuild the project dashboard and task workspace with dense task hierarchy, status controls, member summary, activity timeline, loading/empty/error states, and project-scoped action affordances in frontend/src/features/projects/ProjectDashboardPage.tsx, frontend/src/features/projects/ProjectCreatePage.tsx, frontend/src/features/projects/ProjectMembersPanel.tsx, frontend/src/features/tasks/TaskTree.tsx, frontend/src/features/tasks/TaskForm.tsx, and frontend/src/features/tasks/TaskStatusControl.tsx
- [X] T173 Rebuild the submission and review workspace with draft version navigation, weekly report history, review queue, inline comment timeline, comment thread controls, review status controls, and archived/unauthorized explanations in frontend/src/features/submissions/DraftSubmissionPage.tsx, frontend/src/features/submissions/DraftVersionHistory.tsx, frontend/src/features/submissions/WeeklyReportPage.tsx, frontend/src/features/submissions/WeeklyReportHistory.tsx, frontend/src/features/submissions/ReviewQueuePage.tsx, frontend/src/features/submissions/InlineCommentPanel.tsx, frontend/src/features/submissions/CommentThread.tsx, and frontend/src/features/submissions/ReviewStatusControl.tsx
- [X] T174 Rebuild the resource booking workspace with searchable resources, availability controls, conflict explanation, booking form, immutable started-booking states, and destructive confirmation flow in frontend/src/features/resources/ResourceListPage.tsx, frontend/src/features/resources/BookingCalendar.tsx, frontend/src/features/resources/BookingForm.tsx, frontend/src/features/resources/BookingActions.tsx, and frontend/src/features/resources/BookingConflictAlert.tsx
- [X] T175 Rebuild notification and account administration surfaces with delivery status, project context, action paths, retry/failure states, dense account management controls, and role-safe navigation in frontend/src/features/notifications/NotificationList.tsx and frontend/src/features/admin/AccountAdminPage.tsx
- [X] T176 [P] Update full-stack Playwright flows for production UI landmarks, role workspaces, project setup, submissions/review, bookings, archived read-only behavior, and accessibility assertions in frontend/tests/e2e/accessibility.spec.ts, frontend/tests/e2e/role-workspaces.spec.ts, frontend/tests/e2e/project-work.spec.ts, frontend/tests/e2e/submission-review.spec.ts, frontend/tests/e2e/resource-booking.spec.ts, and frontend/tests/e2e/archived-project.spec.ts
- [X] T177 [P] Add production layout screenshot checks for desktop, tablet, mobile, light theme, dark theme, no-overlap validation, and core workspace states in frontend/tests/e2e/production-ui.spec.ts
- [X] T178 Add route-level code splitting and bundle guard coverage for large workspace routes, Tailwind content scanning, and generated CSS scope in frontend/src/routes/index.tsx, frontend/vite.config.ts, and frontend/tests/component/role-navigation.test.tsx
- [X] T179 Add CI and generated-artifact safeguards for Tailwind/shadcn build outputs, linting, component tests, full-stack Playwright tests, ignored generated files, and Docker build context in .github/workflows/release.yml, scripts/check-generated-artifacts.sh, .gitignore, and .dockerignore
- [X] T180 Update production frontend validation guidance, shadcn component workflow, Tailwind token rules, Scenario 7 checks, and administrator account notes in README.md, docs/production.md, and specs/001-research-group-ops/quickstart.md

### Phase 13 Dependencies

- Phase 13 depends on completed Phase 12 production, CI/CD, and full-stack e2e foundations.
- T165 and T166 block all Tailwind/shadcn implementation tasks.
- T167 and T168 block T171 through T175 because workspaces must use shared primitives instead of one-off controls.
- T169 and T170 must be added before or with T171 so the shell and design-system contract are test-constrained.
- T171 must complete before T172 through T175 route-level workspace rewrites.
- T172, T173, T174, and T175 can proceed in parallel after T168 and T171 when separate developers own each workflow.
- T176 and T177 run after their corresponding workspace rewrites are functional.
- T178, T179, and T180 are final validation and release-hardening tasks.

### Phase 13 Independent Test Criteria

- The frontend passes `npm run build`, `npm run lint`, component tests, and full-stack Playwright tests with Tailwind CSS and shadcn/ui enabled.
- Every project-scoped route exposes the selected project context before create, submit, review, comment, book, cancel, archive, or reopen actions.
- Advisor, student, and admin workspaces remain role-aware and keyboard accessible across desktop, tablet, and mobile layouts.
- Project dashboard, submission review, booking, notification, and account management screens show distinct loading, empty, filtered-empty, warning, error, and success states.
- Screenshot/layout checks confirm core workspace surfaces do not overlap text, controls, status messages, or project context in light or dark theme.

### Phase 13 Parallel Examples

```bash
Task: "T167 [P] Add shadcn/ui base primitives for buttons, forms, overlays, navigation surfaces, feedback, and dense records in frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/textarea.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/alert-dialog.tsx, frontend/src/components/ui/dropdown-menu.tsx, frontend/src/components/ui/popover.tsx, frontend/src/components/ui/tabs.tsx, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/table.tsx, frontend/src/components/ui/toast.tsx, frontend/src/components/ui/skeleton.tsx, frontend/src/components/ui/alert.tsx, and frontend/src/components/ui/tooltip.tsx"
Task: "T168 [P] Add GradSync shared UI adapters for page shell, project context, data states, confirmations, feedback, forms, status badges, and typed workspace composition in frontend/src/shared/ui/PageShell.tsx, frontend/src/shared/ui/ProjectContextBar.tsx, frontend/src/shared/ui/DataState.tsx, frontend/src/shared/ui/ConfirmDialog.tsx, frontend/src/shared/ui/FeedbackProvider.tsx, frontend/src/shared/ui/FormField.tsx, and frontend/src/shared/ui/StatusBadge.tsx"
Task: "T169 [P] Add component tests for Tailwind/shadcn primitives, shared UI adapters, focus behavior, theme switching, toasts, skeletons, dialogs, tooltips, and live-region feedback in frontend/tests/component/design-system.test.tsx"
Task: "T170 [P] Add component tests for the production workspace shell, role-aware navigation, project context visibility, responsive states, and route guards in frontend/tests/component/role-navigation.test.tsx"
```

```bash
Task: "T172 Rebuild the project dashboard and task workspace with dense task hierarchy, status controls, member summary, activity timeline, loading/empty/error states, and project-scoped action affordances in frontend/src/features/projects/ProjectDashboardPage.tsx, frontend/src/features/projects/ProjectCreatePage.tsx, frontend/src/features/projects/ProjectMembersPanel.tsx, frontend/src/features/tasks/TaskTree.tsx, frontend/src/features/tasks/TaskForm.tsx, and frontend/src/features/tasks/TaskStatusControl.tsx"
Task: "T173 Rebuild the submission and review workspace with draft version navigation, weekly report history, review queue, inline comment timeline, comment thread controls, review status controls, and archived/unauthorized explanations in frontend/src/features/submissions/DraftSubmissionPage.tsx, frontend/src/features/submissions/DraftVersionHistory.tsx, frontend/src/features/submissions/WeeklyReportPage.tsx, frontend/src/features/submissions/WeeklyReportHistory.tsx, frontend/src/features/submissions/ReviewQueuePage.tsx, frontend/src/features/submissions/InlineCommentPanel.tsx, frontend/src/features/submissions/CommentThread.tsx, and frontend/src/features/submissions/ReviewStatusControl.tsx"
Task: "T174 Rebuild the resource booking workspace with searchable resources, availability controls, conflict explanation, booking form, immutable started-booking states, and destructive confirmation flow in frontend/src/features/resources/ResourceListPage.tsx, frontend/src/features/resources/BookingCalendar.tsx, frontend/src/features/resources/BookingForm.tsx, frontend/src/features/resources/BookingActions.tsx, and frontend/src/features/resources/BookingConflictAlert.tsx"
Task: "T175 Rebuild notification and account administration surfaces with delivery status, project context, action paths, retry/failure states, dense account management controls, and role-safe navigation in frontend/src/features/notifications/NotificationList.tsx and frontend/src/features/admin/AccountAdminPage.tsx"
```

### Phase 13 Delivery Strategy

1. Complete T165 through T171 first as the production frontend foundation.
2. Deliver US1-facing project dashboard and task workspace through T172 as the first independently reviewable increment.
3. Deliver US2 submission/review and US3 booking workspaces through T173 and T174.
4. Complete notification/admin surfaces, e2e coverage, screenshot validation, bundle checks, CI safeguards, and documentation through T175 through T180.

---

## Phase 14: Specification Governance Alignment

**Purpose**: Resolve the stricter constitution gates exposed by clarification before implementing the newly expanded paper library, code library, and language switching scope.

- [X] T181 [Docs] Add the five constitution-mandated specification modules for business background/user roles/core goals, positive flows, exception/boundary/degradation scenarios, automatable AC, and dependencies/unsupported capabilities in specs/001-research-group-ops/spec.md (AC: Constitution II); self-check: each required module has an explicit heading and maps to existing user stories.
- [X] T182 [Docs] Add measurable success criteria for paper import duplicate handling, paper/code search and authorized downloads, code upload/version conflict handling, and account-level locale switching in specs/001-research-group-ops/spec.md (AC: SC-009..SC-012); self-check: each new outcome is quantifiable and technology-agnostic.
- [X] T183 [Docs] Record testing and development stakeholder review status or remaining blockers in specs/001-research-group-ops/spec.md and specs/001-research-group-ops/plan.md (AC: Constitution II); self-check: implementation remains blocked unless review is approved or risk is explicitly recorded.
- [X] T184 [Docs] Revalidate and update the requirements checklist after T181-T183 in specs/001-research-group-ops/checklists/requirements.md (AC: checklist); self-check: only checkbox markers change and pass count reflects the updated spec.

**Checkpoint**: Specification governance gaps are explicit and measurable before US4 implementation begins.

---

## Phase 15: User Story 4 - Manage Research Assets and Language Preference (Priority: P2)

**Goal**: Project members import/search/download project-scoped papers, upload/search/download versioned code artifacts, and switch the authenticated workspace between Chinese and English with an account-level persisted preference.

**Independent Test**: Import duplicate and non-duplicate papers into one project, upload code artifacts to two different projects, search and download authorized assets, verify unrelated project assets are invisible and unauthorized downloads are rejected, then switch Chinese/English on one signed-in session and verify the preference follows the same account on another session without losing route or project context.

### Tests for User Story 4

> Write these tests first and ensure they fail for the missing behavior before implementation.

- [X] T185 [P] [US4] [Test] Add contract tests for project paper list/create/import/commit/download endpoints in backend/tests/contract/test_papers_api.py (AC: FR-021, FR-022, FR-027, FR-028); self-check: covers accepted import, duplicate response, upload rejection, and 403 download.
- [X] T186 [P] [US4] [Test] Add contract tests for project code artifact create/version upload/download endpoints in backend/tests/contract/test_code_artifacts_api.py (AC: FR-024, FR-025, FR-027, FR-028); self-check: covers version/reference uniqueness, unsupported archive, oversized archive, and 403 download.
- [X] T187 [P] [US4] [Test] Add contract tests for account locale get/update endpoints in backend/tests/contract/test_locale_api.py (AC: FR-026); self-check: verifies only en and zh are accepted and response persists by account.
- [X] T188 [P] [US4] [Test] Add unit tests for paper DOI/external-id normalization, title-first-author-year fingerprinting, and duplicate precedence in backend/tests/unit/test_paper_duplicate_rules.py (AC: FR-022); self-check: checksum wins over DOI/external ID, which wins over normalized title-first-author-year.
- [X] T189 [P] [US4] [Test] Add unit tests for paper/code upload size, content type, extension, checksum, and executable-risk validation in backend/tests/unit/test_asset_upload_policy.py (AC: FR-028); self-check: rejects paper files over 50 MB or outside PDF/BibTeX/text metadata and code files over 200 MB or outside zip/tar.gz.
- [X] T190 [P] [US4] [Test] Add unit tests for code artifact version/reference uniqueness across active, archived, and superseded versions in backend/tests/unit/test_code_artifact_rules.py (AC: FR-025); self-check: duplicate version labels and commit references fail within the same project even after supersede/archive.
- [X] T191 [P] [US4] [Test] Add integration tests for project-scoped paper/code search, cross-project isolation, download authorization, and download audit records in backend/tests/integration/test_research_assets_project_scope.py (AC: FR-021, FR-024, FR-027); self-check: removed or unrelated members cannot discover or download assets.
- [X] T192 [P] [US4] [Test] Add frontend component tests for paper library import/search/detail, code artifact upload/version detail, download states, and language switcher behavior in frontend/tests/component/research-assets-locale.test.tsx (AC: UX-006, UX-007, FR-026); self-check: tests loading, empty, duplicate, validation, success, and unauthorized states.
- [X] T193 [P] [US4] [Test] Add full-stack Playwright flow for paper import duplicate prevention, code upload/download isolation, and cross-session locale persistence in frontend/tests/e2e/research-assets-locale.spec.ts (AC: US4/AC1..AC4); self-check: runs against real Django API and seeded project memberships.

### Implementation for User Story 4

- [X] T194 [P] [US4] [Backend] Create library and repositories Django app configs and register them in backend/apps/library/apps.py, backend/apps/repositories/apps.py, backend/apps/library/__init__.py, backend/apps/repositories/__init__.py, and backend/gradsync/settings/base.py (AC: plan: module boundaries); self-check: django app loading succeeds in test settings.
- [X] T195 [P] [US4] [Backend] Implement PaperRecord, PaperAttachment, and PaperImportBatch models in backend/apps/library/models.py (AC: FR-021, FR-022); self-check: models include project_id, metadata fields, checksum, status, uploader, and import result fields from data-model.md.
- [X] T196 [P] [US4] [Backend] Implement CodeArtifact and CodeArtifactVersion models in backend/apps/repositories/models.py (AC: FR-024, FR-025); self-check: models include project_id, tags, version_label, commit_reference, checksum, file metadata, uploader, and status.
- [X] T197 [P] [US4] [Backend] Implement DownloadEvent persistence and audit mirroring in backend/apps/audit/models.py and backend/apps/audit/services.py (AC: FR-027, FR-018); self-check: successful paper/code downloads create both download and audit-visible records.
- [X] T198 [US4] [Backend] Create migrations for library, repositories, download events, and locale preference changes in backend/apps/library/migrations/0001_initial.py, backend/apps/repositories/migrations/0001_initial.py, backend/apps/audit/migrations/0002_download_event.py, and backend/apps/accounts/migrations/0002_locale_preference.py (AC: data-model); self-check: migrations apply cleanly on an empty test database.
- [X] T199 [US4] [Backend] Implement paper metadata normalization and duplicate detection services in backend/apps/library/duplicate_services.py (AC: FR-022); self-check: duplicate explanations use checksum, DOI/external ID, then title-first-author-year precedence.
- [X] T200 [US4] [Backend] Implement paper import staging, BibTeX/text metadata parsing, file checksum calculation, and upload policy validation in backend/apps/library/import_services.py and backend/apps/library/upload_policy.py (AC: FR-021, FR-022, FR-028); self-check: rejected imports store no file and return the violated rule.
- [X] T201 [US4] [Backend] Implement code artifact upload, version uniqueness, supersede/archive, checksum calculation, and archive policy validation in backend/apps/repositories/services.py and backend/apps/repositories/upload_policy.py (AC: FR-024, FR-025, FR-028); self-check: same-project version/reference duplicates are rejected across active, archived, and superseded versions.
- [X] T202 [US4] [Backend] Implement shared paper/code download authorization and descriptor service in backend/apps/common/downloads.py (AC: FR-027); self-check: service re-checks current project membership at request time before returning a file descriptor or signed URL.
- [X] T203 [US4] [Backend] Implement account-level locale preference service in backend/apps/accounts/locale_services.py (AC: FR-026); self-check: preference is persisted per user and unsupported locales fall back to English without changing stored research content.
- [X] T204 [US4] [Backend] Implement paper serializers and import result schemas in backend/apps/library/serializers.py (AC: contracts/openapi.yaml); self-check: serializer fields match PaperRecord, PaperAttachment, PaperImportBatch, and PaperImportResult contract names.
- [X] T205 [US4] [Backend] Implement paper library viewsets for list/create/import/commit/download in backend/apps/library/views.py and backend/apps/library/urls.py (AC: FR-021, FR-022, FR-027, FR-028); self-check: every queryset is project-scoped and every mutation rejects archived projects.
- [X] T206 [US4] [Backend] Implement code artifact serializers, viewsets, and URLs in backend/apps/repositories/serializers.py, backend/apps/repositories/views.py, and backend/apps/repositories/urls.py (AC: FR-024, FR-025, FR-027, FR-028); self-check: endpoints match openapi operation intent and enforce project membership.
- [X] T207 [US4] [Backend] Implement locale preference serializer, views, and URL wiring in backend/apps/accounts/serializers.py, backend/apps/accounts/views.py, and backend/apps/accounts/urls.py (AC: FR-026); self-check: GET and PATCH /account/locale return account-level preference.
- [X] T208 [US4] [Backend] Wire library and repositories routes into backend/gradsync/urls.py (AC: contracts/openapi.yaml); self-check: route names resolve for papers, imports, code artifacts, version upload, and downloads.
- [X] T209 [US4] [Backend] Include paper imports, code uploads, downloads, and locale changes in audit/activity services in backend/apps/audit/services.py and backend/apps/projects/views.py (AC: FR-010, FR-018, FR-027); self-check: project activity shows only authorized project asset events.
- [X] T210 [US4] [Backend] Extend demo and performance seed commands with papers, code artifacts, duplicate cases, download events, and locale preferences in backend/apps/accounts/management/commands/seed_demo_research_ops.py and backend/apps/projects/management/commands/seed_performance_research_ops.py (AC: quickstart, PERF-006, PERF-007); self-check: seeded data supports US4 e2e and performance tests.
- [X] T211 [P] [US4] [Frontend] Implement typed API clients and TanStack Query hooks for papers, imports, code artifacts, downloads, and locale in frontend/src/features/library/api.ts, frontend/src/features/repositories/api.ts, frontend/src/features/i18n/api.ts, and frontend/src/shared/api/downloads.ts (AC: contracts/openapi.yaml); self-check: hooks expose loading/error states and invalidate project-scoped queries after mutations.
- [X] T212 [P] [US4] [Frontend] Implement Chinese/English typed message catalogs, i18n provider, fallback behavior, and localized validation helpers in frontend/src/features/i18n/messages.en.ts, frontend/src/features/i18n/messages.zh.ts, frontend/src/features/i18n/I18nProvider.tsx, and frontend/src/features/i18n/validation.ts (AC: FR-026, UX-007); self-check: missing application strings fall back to English and are covered by component tests.
- [X] T213 [US4] [Frontend] Add authenticated workspace language switcher and account preference persistence to frontend/src/app/Layout.tsx and frontend/src/features/i18n/LanguageSwitcher.tsx (AC: FR-026, UX-007); self-check: switching locale preserves current route, selected project, keyboard focus, and unsaved-form warning.
- [X] T214 [US4] [Frontend] Implement paper library route with searchable dense list, filters, project context, and filtered-empty states in frontend/src/features/library/PaperLibraryPage.tsx and frontend/src/features/library/PaperFilters.tsx (AC: FR-021, FR-023, UX-006); self-check: unrelated project papers are not rendered from API results.
- [X] T215 [US4] [Frontend] Implement paper import panel with file/DOI/BibTeX metadata input, upload progress, duplicate review, and partial failure states in frontend/src/features/library/PaperImportPanel.tsx and frontend/src/features/library/DuplicateReviewPanel.tsx (AC: FR-022, FR-028, UX-006); self-check: duplicate reasons distinguish checksum, DOI/external ID, and title-author-year.
- [X] T216 [US4] [Frontend] Implement paper detail panel with metadata editing, attachments, tags, notes, download action, and recent download audit summary in frontend/src/features/library/PaperDetailPanel.tsx (AC: FR-021, FR-027, UX-006); self-check: unauthorized or archived-project downloads render disabled controls with explanation.
- [X] T217 [US4] [Frontend] Implement code repository route with searchable artifact list, filters, latest version summary, and project context in frontend/src/features/repositories/CodeRepositoryPage.tsx and frontend/src/features/repositories/CodeArtifactFilters.tsx (AC: FR-024, UX-006); self-check: unrelated project code artifacts are not visible or searchable.
- [X] T218 [US4] [Frontend] Implement code artifact upload, version detail, supersede/archive confirmation, conflict feedback, and download controls in frontend/src/features/repositories/CodeArtifactUploadForm.tsx, frontend/src/features/repositories/CodeArtifactVersionPanel.tsx, and frontend/src/features/repositories/CodeArtifactActions.tsx (AC: FR-024, FR-025, FR-027, FR-028); self-check: duplicate checksum/version conflicts show the existing version and next action.
- [X] T219 [US4] [Frontend] Add paper library, code repository, and locale-aware navigation routes to frontend/src/routes/index.tsx and frontend/src/app/Layout.tsx (AC: UX-002, UX-007); self-check: advisor/student navigation exposes authorized asset routes with localized labels.
- [X] T220 [US4] [Frontend] Add reusable upload progress, download status, duplicate alert, and localized validation state components in frontend/src/shared/ui/UploadProgress.tsx, frontend/src/shared/ui/DownloadStatus.tsx, frontend/src/shared/ui/DuplicateAlert.tsx, and frontend/src/shared/ui/LocalizedValidation.tsx (AC: UX-003, UX-006, UX-007); self-check: states use accessible live regions and do not resize fixed controls.
- [X] T221 [US4] [Test] Add backend performance tests for paper/code search and paper duplicate batch detection in backend/tests/integration/test_research_asset_performance.py (AC: PERF-006, PERF-007); self-check: 1,000 papers, 250 code artifacts, and 100 import records meet spec thresholds.
- [X] T222 [US4] [Test] Add accessibility and responsive layout checks for paper library, code repository, and language switching in frontend/tests/e2e/research-assets-locale.spec.ts and frontend/tests/e2e/production-ui.spec.ts (AC: UX-004, UX-006, UX-007); self-check: desktop, tablet, and mobile layouts have no overlapping text or controls.
- [X] T223 [US4] [CI] Update OpenAPI drift, generated-artifact, and CI e2e guards for library/repository/i18n routes in scripts/check-openapi-contract.sh, scripts/check-generated-artifacts.sh, .github/workflows/release.yml, and frontend/playwright.config.ts (AC: CI/CD Gate Rules); self-check: CI fails on contract drift, generated runtime artifacts, or missing US4 e2e coverage.
- [X] T224 [US4] [Docs] Update quickstart Scenario 8 for paper import, code artifact upload/download, and language switching in specs/001-research-group-ops/quickstart.md and README.md (AC: quickstart); self-check: scenario commands and expected UI/API outcomes are runnable from a clean local environment.
- [X] T225 [US4] [Docs] Update data model and frontend UI contracts after implementation details are finalized in specs/001-research-group-ops/data-model.md and specs/001-research-group-ops/contracts/frontend-ui.md (AC: Documentation Rules); self-check: model fields, UI states, and unsupported capabilities match code and spec.
- [X] T226 [US4] [Test] Run US4 validation suite and record outcomes in specs/001-research-group-ops/quickstart-results.md (AC: US4/AC1..AC4, PERF-006, PERF-007); self-check: backend contract/unit/integration tests, frontend component tests, full-stack Playwright, build, lint, and generated-artifact checks pass or failures are documented with owners.

**Checkpoint**: User Story 4 is independently functional and testable without weakening project isolation, download authorization, upload safety, or account-level locale behavior.

### Phase 15 Dependencies

- Phase 15 depends on Phase 14 specification governance tasks and completed Phase 13 frontend foundation.
- T185 through T193 must be created before implementation tasks and should fail until US4 behavior exists.
- T194 through T198 establish backend app/model foundations before services and endpoints.
- T199 through T203 block serializer/view implementation for their respective domains.
- T204 through T208 expose backend contracts before frontend API hooks in T211.
- T211 and T212 block frontend workspace tasks T213 through T220.
- T214 through T218 can proceed in parallel after T211 when separate developers own paper and code workflows.
- T221 through T226 are final validation, CI, and documentation tasks after the workflow is functional.

### Phase 15 Parallel Examples

```bash
Task: "T185 [P] [US4] [Test] Add contract tests for project paper list/create/import/commit/download endpoints in backend/tests/contract/test_papers_api.py"
Task: "T186 [P] [US4] [Test] Add contract tests for project code artifact create/version upload/download endpoints in backend/tests/contract/test_code_artifacts_api.py"
Task: "T187 [P] [US4] [Test] Add contract tests for account locale get/update endpoints in backend/tests/contract/test_locale_api.py"
Task: "T192 [P] [US4] [Test] Add frontend component tests for paper library import/search/detail, code artifact upload/version detail, download states, and language switcher behavior in frontend/tests/component/research-assets-locale.test.tsx"
```

```bash
Task: "T195 [P] [US4] [Backend] Implement PaperRecord, PaperAttachment, and PaperImportBatch models in backend/apps/library/models.py"
Task: "T196 [P] [US4] [Backend] Implement CodeArtifact and CodeArtifactVersion models in backend/apps/repositories/models.py"
Task: "T197 [P] [US4] [Backend] Implement DownloadEvent persistence and audit mirroring in backend/apps/audit/models.py and backend/apps/audit/services.py"
Task: "T211 [P] [US4] [Frontend] Implement typed API clients and TanStack Query hooks for papers, imports, code artifacts, downloads, and locale in frontend/src/features/library/api.ts, frontend/src/features/repositories/api.ts, frontend/src/features/i18n/api.ts, and frontend/src/shared/api/downloads.ts"
```

### Updated Incremental Delivery

1. Keep US1 as the baseline MVP for project identity, membership, task hierarchy, and isolation.
2. Keep US2 and US3 independently releasable after US1.
3. Deliver US4 after Phase 14 and Phase 13 because research asset workflows require the production workspace shell, upload/download primitives, and locale-aware navigation.
4. Treat paper/code download authorization and project isolation as release blockers for US4.
