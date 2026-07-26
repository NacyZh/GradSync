# Tasks: Research Execution Loop

**Input**: Design documents from `/specs/017-research-execution-loop/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `contracts/frontend-ui.md`, `quickstart.md`

**Tests**: GradSync constitution requires TDD. Every test task below must be
written and observed failing for the missing behavior before its corresponding
implementation task starts. No test exception is approved.

**Organization**: Tasks are grouped by independently testable user story.
Every task is scoped to eight hours or less, identifies an ownership area,
references exact files, and includes a concrete self-check.

## Phase 1: Setup and Governance

**Purpose**: Make feature 017 discoverable by repository governance, CI, and
developers before runtime work begins.

- [X] T001 [P] [CI] Add a current-template boundary-heading fingerprint regression in `scripts/tests/test_check_spec_acceptance.py`, preserve old/new heading compatibility in `.specify/acceptance-policy.json`, and create pending evidence in `specs/017-research-execution-loop/acceptance.json`; self-check: changing the 017 exception section stales decisions and validate mode succeeds without falsely accepting any discipline (AC: plan review gate)
- [X] T002 [P] [Docs] Add documented notification, analytics, and batch-size defaults from `quickstart.md` to `.env.example`, `.env.production.example`, and `docs/production.md`; self-check: names/defaults/min-max relationships match `plan.md` and no secret is introduced (AC: AC-004, AC-016)
- [X] T003 [P] [CI] Extend path/parameter normalization for notification, milestone, deliverable, template-version, decision, and risk identifiers in `scripts/check-openapi-contract.sh`; self-check: a fixture contract and generated schema normalize every new snake_case path parameter consistently (AC: plan contract gate)
- [X] T004 [P] [Test] Add reusable milestone, deliverable, report-template, reporting-period, decision, risk, and actionable-notification factories in `backend/tests/factories/research_execution.py`; self-check: each factory creates the minimum valid same-project graph and supports explicit role overrides (AC: plan TDD gate)
- [X] T005 [P] [Test] Add frontend builders for execution, report, risk, decision, and notification API payloads in `frontend/tests/fixtures/researchExecution.ts`; self-check: builders produce both locale variants and role capability permutations without `any` casts (AC: plan TDD gate)
- [X] T006 [CI] Require all feature 017 specification/design/task/contract/acceptance artifacts in `scripts/check-generated-artifacts.sh`; self-check: deleting any required 017 artifact makes the guard fail with its exact path (AC: plan artifact gate)

**Checkpoint**: Feature 017 is visible to governance and contract tooling.

---

## Phase 2: Foundational Capabilities

**Purpose**: Establish shared authorization, concurrency, pagination, audit,
configuration, event, and frontend-boundary behavior required by every story.

**Critical**: No story implementation begins until T007-T018 pass.

### Foundation Tests

- [X] T007 [P] [Test] Add the primary-advisor, co-advisor, reviewer, observer, student, administrator, removed-member, and unrelated-user execution capability matrix in `backend/tests/unit/test_project_execution_capabilities.py`; self-check: tests fail until read/write/recommend/decide/template/decision/risk/policy capabilities are explicit (AC: AC-012)
- [X] T008 [P] [Test] Add optimistic-version and idempotency helper tests in `backend/tests/unit/test_concurrency_helpers.py`; self-check: stale versions return current safe state and duplicate keys produce one effective mutation under concurrent calls (AC: AC-001, AC-006, AC-011)
- [X] T009 [P] [Test] Add bounded cursor, date-range, and page-size rule tests in `backend/tests/unit/test_research_execution_bounds.py`; self-check: page size cannot exceed 100 and report analytics cannot exceed 104 periods (AC: AC-002, AC-007, AC-009)
- [X] T010 [P] [Test] Add safe execution audit/event payload tests in `backend/tests/unit/test_research_execution_audit.py`; self-check: actor/action/target/outcome remain attributable while report bodies, rationale bodies, URLs, emails, tokens, and file metadata are absent (AC: AC-013)
- [X] T011 [P] [Test] Extend frontend private-import and project-query invalidation expectations in `frontend/tests/component/frontend-import-boundaries.test.ts` and `frontend/tests/component/project-live-refresh.test.tsx`; self-check: features may use only public exports and every planned execution query key invalidates from project events (AC: AC-003, AC-012)

### Foundation Implementation

- [X] T012 [Backend] Extend centralized project capabilities for all feature 017 reads/actions in `backend/apps/projects/access_services.py`; self-check: T007 passes and administrators receive supervision capabilities without ordinary ownership (AC: AC-012)
- [X] T013 [P] [Backend] Implement reusable expected-version conflict and transaction idempotency helpers in `backend/apps/common/concurrency.py`; self-check: T008 passes for create/action/update races without exposing hidden current records (AC: AC-001, AC-006, AC-011)
- [X] T014 [P] [Backend] Implement bounded cursor/page/date-range validation helpers in `backend/apps/common/pagination.py` and `backend/apps/common/ranges.py`; self-check: T009 passes and callers cannot request unbounded lists or analytics windows (AC: AC-002, AC-007, AC-009)
- [X] T015 [Backend] Add sanitized `record_execution_event` and fail-closed privileged-event support in `backend/apps/audit/services.py`; self-check: T010 passes and one committed privileged mutation produces exactly one safe event (AC: AC-013)
- [X] T016 [P] [Backend] Extend project event feed target typing and cursor tests in `backend/apps/projects/services.py` and `backend/tests/integration/test_project_live_events.py`; self-check: committed execution events appear once in order and rolled-back events never appear (AC: AC-003, AC-006, AC-011)
- [X] T017 [P] [Frontend] Add public execution query-key registration and event invalidation in `frontend/src/features/projects/index.ts` and `frontend/src/features/projects/useProjectLiveRefresh.ts`; self-check: T011 passes without importing submissions/notifications private APIs or resetting selected list detail (AC: AC-003, AC-012)
- [X] T018 [Ops] Validate configuration bounds and expose safe default/readiness diagnostics in `backend/gradsync/settings/base.py` and `backend/apps/common/production_checks.py`; self-check: invalid production min/max/cache/batch settings fail readiness while defaults pass (AC: AC-004, AC-016)

**Checkpoint**: Shared foundation passes and all four stories may begin their
test-first phases.

---

## Phase 3: User Story 1 - Close the Notification Loop (Priority: P1) MVP

**Goal**: Separate notification delivery, reading, acknowledgement, business
action, expiry, retry, and escalation; add bounded preferences and operational
visibility.

**Independent Test**: Generate informational, acknowledgement-required,
action-required, reminder, escalation, and failed-delivery records for two
projects; verify filters, deep links, state transitions, policy bounds,
deduplication, privacy, and degradation without implementing milestones or
structured reports.

### Tests for User Story 1

- [X] T019 [P] [US1] [Test] Add notification outcome transition, read-independence, terminal-state, and idempotency unit tests in `backend/tests/unit/test_notification_outcomes.py`; self-check: all seven delivery/outcome distinctions fail before model/service implementation (AC: AC-001)
- [X] T020 [P] [US1] [Test] Add quiet-hours, category-channel, mandatory-security, and timezone unit tests in `backend/tests/unit/test_notification_preferences.py`; self-check: recipient choices never disable in-app, security delivery, due dates, or escalation (AC: AC-004)
- [X] T021 [P] [US1] [Test] Add system-default and bounded primary-advisor project-policy tests in `backend/tests/unit/test_project_notification_policy.py`; self-check: co-advisor/student/admin ordinary writes and out-of-range values are rejected (AC: AC-004, AC-012)
- [X] T022 [P] [US1] [Test] Add notification list/read/acknowledge/preferences/project-policy/admin-summary contract tests in `backend/tests/contract/test_actionable_notifications_api.py`; self-check: all US1 OpenAPI operations, filters, pagination, capabilities, legacy `throughId`, and error statuses fail before endpoints exist (AC: AC-001, AC-002, AC-004)
- [X] T023 [P] [US1] [Test] Add dedupe, acknowledgement, authoritative action reconciliation, reminder, escalation, and concurrency tests in `backend/tests/integration/test_notification_follow_up.py`; self-check: repeated events/jobs create one active follow-up and client calls cannot forge action completion (AC: AC-001, AC-003, AC-004)
- [X] T024 [P] [US1] [Test] Add email attempt, quiet-hour deferral, retry exhaustion, in-app fallback, and masked failure tests in `backend/tests/integration/test_notification_delivery_attempts.py`; self-check: failed email never appears sent and authoritative reads remain available without Redis/email (AC: AC-001, AC-004, AC-016)
- [X] T025 [P] [US1] [Test] Add mixed-recipient filter, stale-target, revoked-access, and administrator-summary privacy tests in `backend/tests/integration/test_notification_security.py`; self-check: 100 fixtures return every eligible item and zero cross-account/project metadata (AC: AC-002, AC-012, AC-013)
- [X] T026 [P] [US1] [Test] Add half-screen drawer, unread/pending-action, acknowledgement, preferences, conflict, toast, keyboard, and bilingual component tests in `frontend/tests/component/actionable-notifications.test.tsx`; self-check: read does not remove pending actions and fixed controls remain non-editable (AC: AC-001, AC-002, AC-014, AC-015)
- [X] T027 [P] [US1] [Test] Add full-stack red-dot, deep-link, acknowledgement, quiet-hours, stale-link, and responsive notification journeys in `frontend/tests/e2e/actionable-notifications.spec.ts`; self-check: 390/900/1440 layouts and linked completion fail before implementation (AC: AC-003, AC-004, AC-014, AC-016)

### Implementation for User Story 1

- [X] T028 [P] [US1] [Backend] Add Notification outcome fields, Notification Delivery Attempt, Notification Preference Profile, Category Preference, and Project Notification Policy models in `backend/apps/notifications/models.py`; self-check: model checks/conditional uniques/indexes match `data-model.md` (AC: AC-001, AC-002, AC-004)
- [X] T029 [US1] [Backend] Create additive notification migration with informational defaults and no fabricated read/acknowledgement/completion in `backend/apps/notifications/migrations/0010_actionable_notification_lifecycle.py`; self-check: old notification fixtures migrate and rollback-compatible reads remain intact (AC: AC-001, AC-013)
- [X] T030 [US1] [Backend] Refactor per-channel attempt creation, summary status, quiet-hour eligibility, masked failure, and retry behavior in `backend/apps/notifications/services.py`; self-check: T020 and T024 pass without changing existing verification/password-recovery delivery semantics (AC: AC-001, AC-004, AC-016)
- [X] T031 [P] [US1] [Backend] Implement user and project policy evaluation with optimistic versions and configured bounds in `backend/apps/notifications/policy_services.py`; self-check: T020-T021 pass and primary advisor is the only project-policy writer (AC: AC-004, AC-012)
- [X] T032 [US1] [Backend] Implement dedupe, acknowledge, expire, unavailable, resolver registration, and authoritative action reconciliation in `backend/apps/notifications/outcome_services.py`; self-check: T019 and T023 pass and a read receipt never changes outcome state (AC: AC-001, AC-003)
- [X] T033 [US1] [Backend] Add bounded reminder, escalation, reconciliation, and delivery-attempt jobs plus idempotent Beat registration in `backend/apps/notifications/tasks.py`; self-check: repeated workers/registration create no duplicate task, reminder, escalation, or attempt (AC: AC-003, AC-004, AC-016)
- [X] T034 [P] [US1] [Backend] Extend notification/preference/policy/operations serializers with camelCase compatibility and safe capabilities in `backend/apps/notifications/serializers.py`; self-check: raw failure details and hidden target metadata never serialize (AC: AC-002, AC-012)
- [X] T035 [US1] [Backend] Implement filtered cursor list, selected-ID/legacy read, acknowledgement, preferences, policy, and admin-summary views/routes in `backend/apps/notifications/views.py` and `backend/apps/notifications/urls.py`; self-check: T022 and T025 pass with request-time authorization (AC: AC-001, AC-002, AC-004, AC-012)
- [X] T036 [US1] [Ops] Add notification outcome/delivery/lag metrics, audit events, and readiness checks in `backend/apps/common/views.py`, `backend/apps/audit/services.py`, and `backend/apps/common/production_checks.py`; self-check: metrics expose counts/lag only and privileged policy/acknowledgement evidence is attributable (AC: AC-013, AC-016)
- [X] T037 [P] [US1] [Frontend] Add typed filters, cursor pages, selected read, acknowledge, preferences, and project-policy clients in `frontend/src/features/notifications/api.ts`; self-check: legacy list payload remains accepted and query keys include every filter (AC: AC-001, AC-002)
- [X] T038 [US1] [Frontend] Rebuild the bell drawer and bounded filtered item list in `frontend/src/features/notifications/NotificationCenter.tsx` and `frontend/src/features/notifications/NotificationList.tsx`; self-check: the red dot tracks unread while pending action persists and only loaded IDs are marked read (AC: AC-001, AC-002, AC-014)
- [X] T039 [P] [US1] [Frontend] Add quiet-hours and category email settings to `frontend/src/features/notifications/NotificationPreferences.tsx` and `frontend/src/features/auth/ProfilePage.tsx`; self-check: mandatory security/in-app controls are fixed, conflicts preserve input, and results use global toast (AC: AC-004, AC-014)
- [X] T040 [P] [US1] [Frontend] Add primary-advisor project threshold controls and effective bounds in `frontend/src/features/projects/ProjectNotificationPolicy.tsx` and `frontend/src/features/projects/ProjectDashboardPage.tsx`; self-check: all other roles omit controls and out-of-range fields show localized validation (AC: AC-004, AC-012)
- [X] T041 [US1] [Frontend] Add complete notification outcome, delivery, preference, policy, stale-target, and operations strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: T026 finds zero fallback keys or raw server messages (AC: AC-015)
- [X] T042 [US1] [Test] Run the US1 unit/contract/integration/component/e2e and 1,000-notification performance set and record checkpoint evidence in `specs/017-research-execution-loop/checklists/us1-notifications.md`; self-check: AC-001..AC-004 and relevant AC-012..AC-016 evidence passes independently (AC: AC-001, AC-002, AC-003, AC-004)

**Checkpoint**: Notifications form a complete, independently testable MVP.

---

## Phase 4: User Story 2 - Plan Milestones and Accept Deliverables (Priority: P1)

**Goal**: Add ordered milestones, assigned deliverables, immutable evidence
revisions, reviewer recommendations, advisor final decisions, derived status,
calendar projection, and execution UI.

**Independent Test**: Create, reorder, submit, recommend, return, resubmit,
accept, and archive a multi-milestone project; verify role authority, immutable
history, derivation, event refresh, date projection, and bounded performance.

### Tests for User Story 2

- [ ] T043 [P] [US2] [Test] Add milestone owner/order/derivation/date/archive unit tests in `backend/tests/unit/test_milestone_derivation.py`; self-check: task/progress cannot complete a milestone and derived-state precedence matches `data-model.md` (AC: AC-005)
- [ ] T044 [P] [US2] [Test] Add deliverable assignment/task-link/progress/submission/evidence validation tests in `backend/tests/unit/test_deliverable_rules.py`; self-check: cross-project, empty evidence, unsafe URL, inactive assignee, and invalid transitions fail (AC: AC-005, AC-006, AC-012)
- [ ] T045 [P] [US2] [Test] Add reviewer designation, target assignment, recommendation, and advisor-final-authority tests in `backend/tests/unit/test_deliverable_review_authority.py`; self-check: reviewer opinion never accepts or completes a milestone (AC: AC-005, AC-012)
- [ ] T046 [P] [US2] [Test] Add execution summary, milestone, deliverable, submit, recommendation, decision, and archive contract tests in `backend/tests/contract/test_project_execution_api.py`; self-check: every US2 OpenAPI operation/capability/conflict shape fails before endpoints exist (AC: AC-005, AC-006)
- [ ] T047 [P] [US2] [Test] Add submit-return-resubmit-accept/archive/history integration tests in `backend/tests/integration/test_deliverable_lifecycle.py`; self-check: accepted revision/evidence and prior recommendations remain immutable through every transition (AC: AC-006, AC-011)
- [ ] T048 [P] [US2] [Test] Add stale-update, duplicate-idempotency, simultaneous recommendation/decision, and milestone-reconcile tests in `backend/tests/integration/test_project_execution_concurrency.py`; self-check: exactly one final decision and one derived completion result commit (AC: AC-006)
- [ ] T049 [P] [US2] [Test] Add full role, direct-ID, removed-member, evidence-redaction, and archived/held-project tests in `backend/tests/integration/test_project_execution_security.py`; self-check: no forbidden control or metadata is returned for all eight actors (AC: AC-012, AC-013)
- [ ] T050 [P] [US2] [Test] Add 200-item query-count/search/filter/open-detail performance tests in `backend/tests/integration/test_project_execution_performance.py`; self-check: p95 remains under three seconds without unbounded prefetch (AC: AC-007)
- [ ] T051 [P] [US2] [Test] Add list/detail, member combobox, evidence, revision, recommendation, final-decision, conflict, and role component tests in `frontend/tests/component/project-execution.test.tsx`; self-check: fixed panels, global toast, keyboard, and role-specific commands fail before UI implementation (AC: AC-005, AC-006, AC-012, AC-014)
- [ ] T052 [P] [US2] [Test] Add advisor/student/reviewer/observer/admin full-stack execution journeys in `frontend/tests/e2e/research-execution.spec.ts`; self-check: cross-session convergence and 390/900/1440 layouts fail before route implementation (AC: AC-003, AC-005, AC-006, AC-014)

### Implementation for User Story 2

- [ ] T053 [US2] [Backend] Add Milestone, Owner, Deliverable, Assignee, Reviewer Designation, Task Link, Revision, Evidence, Recommendation, and Final Decision models in `backend/apps/projects/models.py`; self-check: all constraints/indexes/state enums match `data-model.md` (AC: AC-005, AC-006)
- [ ] T054 [US2] [Backend] Create additive execution schema migration in `backend/apps/projects/migrations/0004_research_execution.py`; self-check: existing projects/tasks/materials migrate without rewrite and `migrate --plan` is additive (AC: AC-006, AC-013)
- [ ] T055 [US2] [Backend] Extend Submission Review Assignment with Deliverable Revision target and migration in `backend/apps/submissions/models.py` and `backend/apps/submissions/migrations/0008_deliverable_review_assignments.py`; self-check: exactly-one-target constraint keeps all legacy report/writing/draft assignments valid (AC: AC-006, AC-012)
- [ ] T056 [US2] [Backend] Implement milestone create/update/reorder/archive and transactional derived-state reconciliation in `backend/apps/projects/execution_services.py`; self-check: T043 passes and date-change audit snapshot preserves the former target date (AC: AC-005, AC-006, AC-013)
- [ ] T057 [US2] [Backend] Implement deliverable planning, assignee/reviewer combobox validation, task links, progress, blocked state, and archive behavior in `backend/apps/projects/execution_services.py`; self-check: T044 passes and students cannot change planning fields (AC: AC-005, AC-012)
- [ ] T058 [US2] [Backend] Implement immutable submission revisions, same-project evidence, safe snapshots, idempotency, and target review-assignment creation in `backend/apps/projects/execution_services.py` and `backend/apps/submissions/review_assignment_services.py`; self-check: T045 and submission portions of T047 pass (AC: AC-006, AC-012)
- [ ] T059 [US2] [Backend] Implement reviewer recommendation and primary/co-advisor final decision transactions in `backend/apps/projects/execution_services.py`; self-check: one final decision updates deliverable and milestone atomically and reviewer-only calls fail (AC: AC-005, AC-006, AC-011)
- [ ] T060 [US2] [Backend] Emit execution audit/project events and register assignment/review/decision notification outcome resolvers in `backend/apps/audit/services.py` and `backend/apps/notifications/outcome_services.py`; self-check: linked actions complete only after committed target operations and payloads are minimized (AC: AC-003, AC-013)
- [ ] T061 [P] [US2] [Backend] Add read-only milestone/deliverable date projections and stable source cursors in `backend/apps/schedules/projection_services.py`; self-check: edits produce one updated occurrence and no mutable Schedule Item row (AC: AC-003, AC-006)
- [ ] T062 [P] [US2] [Backend] Implement capability-aware execution summary/milestone/deliverable serializers in `backend/apps/projects/execution_serializers.py`; self-check: reviewer/observer/student payloads omit protected evidence and forbidden action metadata (AC: AC-012)
- [ ] T063 [US2] [Backend] Implement paginated execution summary, milestone, deliverable, submit, recommendation, decision, and archive views/routes in `backend/apps/projects/execution_views.py` and `backend/apps/projects/urls.py`; self-check: T046, T049, and T050 pass with `409` safe current representations (AC: AC-005, AC-006, AC-007, AC-012)
- [ ] T064 [P] [US2] [Frontend] Add typed execution summary/milestone/deliverable clients and public DTO exports in `frontend/src/features/projects/executionApi.ts` and `frontend/src/features/projects/index.ts`; self-check: API types cover every capability/state/revision without cross-feature private imports (AC: AC-005, AC-006)
- [ ] T065 [US2] [Frontend] Register `/projects/:projectId/execution` and the responsive Execution tab shell in `frontend/src/routes/index.tsx` and `frontend/src/features/projects/ProjectExecutionPage.tsx`; self-check: project navigation scrolls at mobile width and selection survives live refresh (AC: AC-003, AC-014)
- [ ] T066 [P] [US2] [Frontend] Build bounded milestone list/detail/create/edit/archive views in `frontend/src/features/projects/MilestoneList.tsx` and `frontend/src/features/projects/MilestoneDetail.tsx`; self-check: status is derived/read-only and member/date/order controls are keyboard complete (AC: AC-005, AC-014)
- [ ] T067 [US2] [Frontend] Build bounded deliverable list/detail/planning/progress views in `frontend/src/features/projects/DeliverableList.tsx` and `frontend/src/features/projects/DeliverableDetail.tsx`; self-check: role-specific fields/actions and stable panel dimensions match the UI contract (AC: AC-005, AC-006, AC-014)
- [ ] T068 [US2] [Frontend] Add searchable evidence selection, submission confirmation, and immutable revision history in `frontend/src/features/projects/DeliverableEvidence.tsx` and `frontend/src/features/projects/DeliverableDetail.tsx`; self-check: unavailable evidence shows safe snapshot and every mutation uses global toast (AC: AC-006, AC-012)
- [ ] T069 [US2] [Frontend] Add assigned reviewer recommendation and separate advisor final-decision controls in `frontend/src/features/submissions/ReviewQueuePage.tsx` and `frontend/src/features/projects/DeliverableDetail.tsx`; self-check: reviewer recommendation cannot display completion and final decision names the exact revision (AC: AC-005, AC-012)
- [ ] T070 [US2] [Frontend] Replace task-only dashboard health with execution summary links and invalidate execution keys in `frontend/src/features/projects/ProjectDashboardPage.tsx` and `frontend/src/features/projects/useProjectLiveRefresh.ts`; self-check: Tasks remain daily work and summary does not duplicate full detail (AC: AC-003, AC-005)
- [ ] T071 [US2] [Frontend] Add complete execution, evidence, recommendation, decision, derivation, calendar, conflict, and empty-state strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: T051 finds no fallback/raw API text (AC: AC-015)
- [ ] T072 [US2] [Test] Run US2 tests and record lifecycle/performance/role checkpoint evidence in `specs/017-research-execution-loop/checklists/us2-deliverables.md`; self-check: AC-005..AC-007 and relevant AC-003/AC-011..AC-015 pass independently (AC: AC-005, AC-006, AC-007)

**Checkpoint**: Project outcomes and evidence acceptance work independently of
structured report and decision/risk UI.

---

## Phase 5: User Story 3 - Submit Structured Reports and Analyze Progress (Priority: P1)

**Goal**: Add controlled bilingual report templates, period-time version
locking, immutable typed responses, existing return/resubmit review, and
source-traceable bounded analytics/export.

**Independent Test**: Publish two template versions across open periods,
submit/return/resubmit reports, migrate historical reports, calculate exact
aggregates including missing values, and export one authorized range without
rankings.

### Tests for User Story 3

- [ ] T073 [P] [US3] [Test] Add all seven field-type, bilingual-label, option, numeric-range, required, order, and publish immutability tests in `backend/tests/unit/test_report_template_fields.py`; self-check: arbitrary fields/formulas and malformed locale definitions fail (AC: AC-008, AC-015)
- [ ] T074 [P] [US3] [Test] Add period opening, one-version lock, scheduler idempotency, archive, and concurrent publication tests in `backend/tests/unit/test_reporting_period_lock.py`; self-check: every student/revision in one period retains exactly one version (AC: AC-008)
- [ ] T075 [P] [US3] [Test] Add response validation, required/missing, execution reference, blocker promotion, and revision tests in `backend/tests/unit/test_structured_report_responses.py`; self-check: responses cannot reference another project or mutate after submission (AC: AC-008, AC-012)
- [ ] T076 [P] [US3] [Test] Add independent expected/on-time/late/missing/review/execution/risk/metric aggregate fixtures in `backend/tests/unit/test_report_analytics.py`; self-check: every exact count/value/source ID and null missing value fails before analytics implementation (AC: AC-009, AC-010)
- [ ] T077 [P] [US3] [Test] Add template/period/report/analytics/export contract tests in `backend/tests/contract/test_structured_reports_api.py`; self-check: every US3 OpenAPI operation, field validation, role capability, range limit, and CSV content type fails before endpoints exist (AC: AC-008, AC-009, AC-010)
- [ ] T078 [P] [US3] [Test] Add publish-open-submit-return-resubmit-history integration tests in `backend/tests/integration/test_structured_report_revisions.py`; self-check: open-period drafts and all revisions keep locked labels/values through newer publication (AC: AC-008)
- [ ] T079 [P] [US3] [Test] Add legacy default-template/period/response backfill and application-rollback tests in `backend/tests/integration/test_report_template_migration.py`; self-check: old columns/status/timestamps remain and no fabricated review/outcome appears (AC: AC-008, AC-013)
- [ ] T080 [P] [US3] [Test] Add role/privacy, source-link, export, no-rank/no-score, cache-degradation, and 500-revision/104-period performance tests in `backend/tests/integration/test_report_analytics_performance.py`; self-check: authorized p95 is under three seconds and Redis loss preserves source reads (AC: AC-009, AC-010, AC-012, AC-016)
- [ ] T081 [P] [US3] [Test] Add Periods/History/Template/Analytics form, version, chart-table, export, conflict, keyboard, and bilingual component tests in `frontend/tests/component/structured-reports.test.tsx`; self-check: all role views and missing-data labels fail before implementation (AC: AC-008, AC-009, AC-010, AC-014, AC-015)
- [ ] T082 [P] [US3] [Test] Add full-stack template publication, period lock, report revision, analytics source, export, locale, and responsive journeys in `frontend/tests/e2e/structured-reports.spec.ts`; self-check: 390/900/1440 views and no-ranking assertions fail before implementation (AC: AC-008, AC-009, AC-010, AC-014)

### Implementation for User Story 3

- [ ] T083 [US3] [Backend] Add Report Template, Template Version, Template Field, Reporting Period, and Report Response models plus Weekly Progress Report extensions in `backend/apps/submissions/models.py`; self-check: field/period/response constraints and indexes match `data-model.md` (AC: AC-008, AC-009)
- [ ] T084 [US3] [Backend] Create additive report schema migration with nullable compatibility fields in `backend/apps/submissions/migrations/0009_structured_reporting.py`; self-check: existing weekly reports remain queryable before backfill (AC: AC-008, AC-013)
- [ ] T085 [US3] [Backend] Create chunked default-template, historical-period, report-link, and response backfill migration in `backend/apps/submissions/migrations/0010_backfill_structured_reports.py`; self-check: T079 passes with preserved legacy narrative/review fields and bounded batches (AC: AC-008, AC-013)
- [ ] T086 [US3] [Backend] Implement draft copy/edit/validate/publish and immutable version behavior in `backend/apps/submissions/report_template_services.py`; self-check: T073 passes and publication affects only later-opened periods (AC: AC-008, AC-015)
- [ ] T087 [US3] [Backend] Implement lazy-safe/scheduled weekly period opening, template locking, closing, and idempotent Beat work in `backend/apps/submissions/report_period_services.py` and `backend/apps/notifications/tasks.py`; self-check: T074 passes and archived projects open no new period (AC: AC-008, AC-016)
- [ ] T088 [US3] [Backend] Extend report submission/return/resubmit services for typed responses, locked version, lateness, source validation, and blocker-to-risk hook in `backend/apps/submissions/report_services.py`; self-check: T075 and T078 pass while legacy payload aliases remain accepted (AC: AC-008, AC-011, AC-012)
- [ ] T089 [US3] [Backend] Implement exact bounded aggregate calculation, source IDs, missing-data semantics, and event-version Redis caching in `backend/apps/submissions/report_analytics.py`; self-check: T076 and non-export portions of T080 pass with no composite score (AC: AC-009, AC-010, AC-016)
- [ ] T090 [P] [US3] [Backend] Implement permission-rechecked bounded CSV analytics export using existing download helpers in `backend/apps/submissions/report_analytics.py`; self-check: exported filters/locale/source IDs equal the authorized screen and no narrative body/rank appears (AC: AC-010, AC-012)
- [ ] T091 [P] [US3] [Backend] Add template/period/report/analytics capability and payload serializers in `backend/apps/submissions/serializers.py`; self-check: historical revisions use their own bilingual field labels and hidden reports never contribute visible source metadata (AC: AC-008, AC-012, AC-015)
- [ ] T092 [US3] [Backend] Implement template, period, structured report, analytics, and export views/routes in `backend/apps/submissions/views.py` and `backend/apps/submissions/urls.py`; self-check: T077 and T080 pass with range/page limits and current-role checks (AC: AC-008, AC-009, AC-010, AC-012)
- [ ] T093 [US3] [Backend] Emit report/template/period audit/project events, actionable notifications, and read-only period deadline projection in `backend/apps/audit/services.py`, `backend/apps/notifications/outcome_services.py`, and `backend/apps/schedules/projection_services.py`; self-check: report submission/review closes linked actions and calendar shows one deadline (AC: AC-003, AC-013)
- [ ] T094 [P] [US3] [Frontend] Extend typed report/template/period/analytics/export clients and public query keys in `frontend/src/features/submissions/api.ts` and `frontend/src/features/submissions/index.ts`; self-check: no projects private API import is introduced (AC: AC-008, AC-009, AC-010)
- [ ] T095 [US3] [Frontend] Refactor Reports into capability-aware Periods/History/Template/Analytics tabs in `frontend/src/features/submissions/WeeklyReportPage.tsx`; self-check: student/advisor/reviewer/observer/admin views match the UI role matrix and preserve selected period (AC: AC-008, AC-012, AC-014)
- [ ] T096 [US3] [Frontend] Build keyboard-orderable controlled bilingual field editor and fixed preview in `frontend/src/features/submissions/ReportTemplateEditor.tsx`; self-check: publishing explains period-lock behavior and arbitrary formulas are absent (AC: AC-008, AC-014, AC-015)
- [ ] T097 [US3] [Frontend] Build period-locked typed report form and immutable revision rendering in `frontend/src/features/submissions/StructuredReportForm.tsx` and `frontend/src/features/submissions/WeeklyReportHistory.tsx`; self-check: return/resubmit uses existing lifecycle and source selectors are project-authorized comboboxes (AC: AC-008, AC-012)
- [ ] T098 [US3] [Frontend] Build bounded analytics summaries, accessible chart tables, source drill-down, missing states, and export in `frontend/src/features/submissions/ReportAnalyticsPanel.tsx`; self-check: every metric shows definition/unit/population/range/missing/source and no ranking language (AC: AC-009, AC-010, AC-014)
- [ ] T099 [US3] [Frontend] Integrate structured report detail/template version into the list/detail review queue in `frontend/src/features/submissions/ReviewQueuePage.tsx`; self-check: assigned reviewers see only assigned reports/comments and advisors preserve current selection (AC: AC-008, AC-012)
- [ ] T100 [US3] [Frontend] Add complete template-field, period, response, analytics, source, export, missing, and review strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: T081 has zero fallback keys and PDF/file labels remain localized (AC: AC-015)
- [ ] T101 [US3] [Ops] Add period-generation, analytics-failure/cache, export, and report-backfill readiness/metrics in `backend/apps/common/production_checks.py` and `backend/apps/common/views.py`; self-check: source reports remain usable while failures/lag are visible without content (AC: AC-013, AC-016)
- [ ] T102 [US3] [Test] Run US3 tests and record migration/aggregate/performance/role checkpoint evidence in `specs/017-research-execution-loop/checklists/us3-reports.md`; self-check: AC-008..AC-010 and relevant AC-003/AC-012..AC-016 pass independently (AC: AC-008, AC-009, AC-010)

**Checkpoint**: Structured reporting and transparent analysis work with empty
or populated milestone/risk sources and remain independently testable.

---

## Phase 6: User Story 4 - Record Decisions and Manage Risks (Priority: P1)

**Goal**: Add immutable/superseding decisions and versioned risks with fixed
3-by-3 severity, source links, triage/treatment/closure/reopen, reminders,
calendar dates, and durable history.

**Independent Test**: Publish and supersede decisions, raise/promote/triage/
mitigate/accept/resolve/reopen risks, exercise all nine matrix cells, and verify
history, links, escalation, role boundaries, and handover retrieval.

### Tests for User Story 4

- [ ] T103 [P] [US4] [Test] Add immutable decision, option/owner/effective-date, supersession uniqueness/cycle, and idempotency tests in `backend/tests/unit/test_decision_rules.py`; self-check: direct edit/delete and branching successor attempts fail (AC: AC-011)
- [ ] T104 [P] [US4] [Test] Add all nine fixed 3-by-3 likelihood/impact outcomes and no-client-severity tests in `backend/tests/unit/test_risk_matrix.py`; self-check: matrix exactly matches `data-model.md` (AC: AC-011)
- [ ] T105 [P] [US4] [Test] Add raise/triage/mitigate/accept/resolve/reopen/owner/date/rationale transition tests in `backend/tests/unit/test_risk_transitions.py`; self-check: terminal reminders stop and reopen restores valid review state (AC: AC-011)
- [ ] T106 [P] [US4] [Test] Add decision/risk list/detail/publish/supersede/triage/transition contract tests in `backend/tests/contract/test_project_governance_records_api.py`; self-check: all US4 OpenAPI operations, filters, capabilities, versions, and errors fail before endpoints exist (AC: AC-011, AC-012)
- [ ] T107 [P] [US4] [Test] Add decision chain, immutable link snapshot, and concurrent supersession integration tests in `backend/tests/integration/test_decision_history.py`; self-check: one successor wins and protected/deleted links disclose only safe snapshots (AC: AC-011, AC-012, AC-013)
- [ ] T108 [P] [US4] [Test] Add blocker promotion dedupe, risk revisions, overdue/high escalation, closure, reopen, and scheduler idempotency tests in `backend/tests/integration/test_risk_lifecycle.py`; self-check: repeated promotion/jobs create one source risk and one active escalation (AC: AC-004, AC-011)
- [ ] T109 [P] [US4] [Test] Add student/advisor/reviewer/observer/admin/removed/unrelated governance read-write and link-redaction tests in `backend/tests/integration/test_project_governance_records_security.py`; self-check: every direct-ID and linked-target path follows both record permissions (AC: AC-012, AC-013)
- [ ] T110 [P] [US4] [Test] Add decision/risk bounded list/detail, supersede, matrix, transition, history, toast, keyboard, and bilingual component tests in `frontend/tests/component/project-governance-records.test.tsx`; self-check: role controls and fixed dimensions fail before UI implementation (AC: AC-011, AC-014, AC-015)
- [ ] T111 [P] [US4] [Test] Add full-stack decision handover, risk lifecycle/escalation, stale-link, live-refresh, and responsive journeys in `frontend/tests/e2e/project-governance-records.spec.ts`; self-check: retrieval under two minutes and 390/900/1440 layouts fail before implementation (AC: AC-003, AC-011, AC-014, AC-018)

### Implementation for User Story 4

- [ ] T112 [US4] [Backend] Add Decision Record, Risk Record, Risk Revision, and Project Record Link models in `backend/apps/projects/models.py`; self-check: immutability, unique successor/source/idempotency, check constraints, matrix fields, and indexes match `data-model.md` (AC: AC-011)
- [ ] T113 [US4] [Backend] Create additive governance-record migration in `backend/apps/projects/migrations/0005_decisions_and_risks.py`; self-check: existing project execution data migrates without update and rollback-compatible reads remain (AC: AC-011, AC-013)
- [ ] T114 [US4] [Backend] Implement bounded same-project source/target link validation, safe snapshots, and read-time redaction in `backend/apps/projects/decision_risk_services.py`; self-check: T107 and T109 link cases pass for every supported target kind (AC: AC-012, AC-013)
- [ ] T115 [US4] [Backend] Implement transactional decision publish/supersede/idempotency and audit behavior in `backend/apps/projects/decision_risk_services.py`; self-check: T103 and T107 pass and published rows have no ordinary edit/delete path (AC: AC-011, AC-013)
- [ ] T116 [US4] [Backend] Implement risk raise/promotion/triage/fixed severity/transition/revision/idempotency behavior in `backend/apps/projects/decision_risk_services.py`; self-check: T104-T105 and non-scheduler T108 cases pass (AC: AC-011, AC-012)
- [ ] T117 [US4] [Backend] Add bounded high/overdue risk reminder/escalation/reconciliation jobs in `backend/apps/notifications/tasks.py`; self-check: accepted/resolved risks stop, reopened risks resume, and repeated scans produce one active escalation (AC: AC-004, AC-011, AC-016)
- [ ] T118 [US4] [Backend] Add capability-aware decision/risk/link/history serializers in `backend/apps/projects/execution_serializers.py`; self-check: protected linked content and private rationale are omitted for reviewer/observer/admin aggregate contexts (AC: AC-012)
- [ ] T119 [US4] [Backend] Implement paginated decision/risk list/detail/publish/supersede/triage/transition views/routes in `backend/apps/projects/execution_views.py` and `backend/apps/projects/urls.py`; self-check: T106 and T109 pass with search/status/severity/owner filters (AC: AC-011, AC-012)
- [ ] T120 [US4] [Backend] Emit decision/risk audit/project events, notification resolvers, milestone-risk reconciliation, and risk-review calendar projections in `backend/apps/audit/services.py`, `backend/apps/notifications/outcome_services.py`, `backend/apps/projects/execution_services.py`, and `backend/apps/schedules/projection_services.py`; self-check: one committed event updates all derived views without duplicate Schedule Item rows (AC: AC-003, AC-011, AC-013)
- [ ] T121 [P] [US4] [Frontend] Add typed decision/risk/link/history/filter clients in `frontend/src/features/projects/executionApi.ts`; self-check: DTOs expose server-derived severity and capabilities without another feature's private API (AC: AC-011, AC-012)
- [ ] T122 [US4] [Frontend] Build bounded immutable decision register/detail and complete-successor flow in `frontend/src/features/projects/DecisionRegister.tsx`; self-check: published rows expose no edit/delete and predecessor/successor context remains visible (AC: AC-011, AC-014, AC-018)
- [ ] T123 [US4] [Frontend] Build bounded risk register/detail, raise dialog, triage matrix, transitions, and revision history in `frontend/src/features/projects/RiskRegister.tsx`; self-check: segmented controls announce derived severity and only permitted next actions render (AC: AC-011, AC-012, AC-014)
- [ ] T124 [US4] [Frontend] Wire Decisions/Risks tabs, execution summary filters, and live query invalidation in `frontend/src/features/projects/ProjectExecutionPage.tsx`, `frontend/src/features/projects/ProjectDashboardPage.tsx`, and `frontend/src/features/projects/useProjectLiveRefresh.ts`; self-check: selection survives background refresh and high/overdue counts link to correct filters (AC: AC-003, AC-011)
- [ ] T125 [US4] [Frontend] Add complete decision, risk matrix, treatment, transition, history, link, escalation, and unavailable strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: T110 finds no fallback or status conveyed by color alone (AC: AC-015)
- [ ] T126 [US4] [Test] Run US4 tests and record lifecycle/security/handover checkpoint evidence in `specs/017-research-execution-loop/checklists/us4-governance.md`; self-check: AC-011..AC-015 and AC-018 pass independently (AC: AC-011, AC-012, AC-013, AC-014, AC-015, AC-018)

**Checkpoint**: Decisions and risks provide durable project governance with
traceable handover.

---

## Phase 7: Polish and Cross-Cutting Release Readiness

**Purpose**: Prove integrated contracts, compatibility, security, locale,
performance, operations, migration, rollback, and acceptance outcomes.

- [ ] T127 [P] [Test] Add strict feature 017 operation/request/response/status coverage to `backend/tests/contract/test_openapi_schema.py`; self-check: `bash scripts/check-openapi-contract.sh --strict-shapes specs/017-research-execution-loop/contracts/openapi.yaml` passes all 41 operations (AC: plan contract gate)
- [ ] T128 [P] [Test] Extend frontend private-import checks for execution/report/notification modules in `frontend/tests/component/frontend-import-boundaries.test.ts`; self-check: all cross-feature access uses `index.ts` public contracts and violations equal zero (AC: AC-012)
- [ ] T129 [P] [Test] Extend translation completeness, raw-message, enum, notification, validation, and CSV-heading checks in `frontend/tests/component/i18n-completeness.test.ts`; self-check: every feature 017 key switches English/Chinese with zero fallback (AC: AC-015)
- [ ] T130 [P] [Test] Extend production overlap, bounded-panel, 200% zoom, reduced-motion, keyboard, chart-table, and screen-reader coverage in `frontend/tests/e2e/production-ui.spec.ts` and `frontend/tests/e2e/accessibility.spec.ts`; self-check: 390/900/1440 CSS px have no overlap, clipping, page overflow, or inaccessible command (AC: AC-014)
- [ ] T131 [Test] Add cross-story authoritative notification completion and project-event convergence tests in `backend/tests/integration/test_research_execution_loop.py` and `frontend/tests/e2e/research-execution.spec.ts`; self-check: deliverable/report/risk/decision operations update notifications and connected sessions within five seconds (AC: AC-003, AC-011)
- [ ] T132 [Test] Add integrated Redis/email/calendar/analytics outage and recovery tests in `backend/tests/integration/test_research_execution_degradation.py`; self-check: source records stay usable, stale state appears within five seconds, and reconciliation creates no duplicates (AC: AC-016)
- [ ] T133 [Test] Run combined 1,000-notification, 200-execution-item, 500-report-revision, 500-governance-record performance fixtures in `backend/tests/integration/test_research_execution_performance.py`; self-check: filtered reads meet three-second p95 and no query/list/fan-out is unbounded (AC: AC-002, AC-007, AC-009)
- [ ] T134 [Ops] Add schema-first rollout, report backfill, backup/restore verification, application-first rollback, and dormant-job steps to `docs/ops/backup-restore-drill.md` and `docs/production.md`; self-check: rollback preserves all new history and legacy tasks/reports/notifications still work (AC: AC-006, AC-008, AC-011, AC-016)
- [ ] T135 [Ops] Add worker/Beat registration, lag/failure/outcome/period/analytics metrics and alert guidance in `backend/apps/common/production_checks.py`, `backend/apps/common/views.py`, and `docs/ops/monitoring-alerts.md`; self-check: readiness catches missing jobs/unsafe bounds and metrics contain no protected content (AC: AC-013, AC-016)
- [ ] T136 [Test] Execute the moderated advisor and timed handover protocols and record anonymized outcomes in `specs/017-research-execution-loop/checklists/usability.md`; self-check: at least 90% complete advisor setup unassisted and retrieve evidence/report/decision/risk within two minutes (AC: AC-017, AC-018)
- [ ] T137 [Docs] Recompute feature 017 normative revision and record Product/Testing/Development decisions only after evidence review in `specs/017-research-execution-loop/acceptance.json`; self-check: pending/rejected/stale decisions keep production enforcement blocked and no decision is auto-accepted (AC: plan review gate)
- [ ] T138 [CI] Run backend migrations, Ruff, full pytest, deploy checks, strict OpenAPI, readiness, and acceptance report commands from `specs/017-research-execution-loop/quickstart.md`; self-check: all backend/contract/operations gates pass and results are recorded in `specs/017-research-execution-loop/checklists/release.md` (AC: AC-001, AC-013, AC-016)
- [ ] T139 [CI] Run frontend ESLint, Vitest, TypeScript/Vite build, PWA check, full-stack Playwright, and generated-artifact guard from `specs/017-research-execution-loop/quickstart.md`; self-check: all frontend/locale/accessibility/responsive gates pass with no generated artifacts (AC: AC-003, AC-014, AC-015)
- [ ] T140 [Ops] Run production smoke, scheduler/worker health, backup restore, migration, rollback rehearsal, and production acceptance enforcement from `scripts/check-production-readiness.sh` and `scripts/deploy-production.sh`; self-check: deployment proceeds only for the accepted current revision and rollback preserves governance evidence (AC: AC-016, plan release gate)

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 Setup** has no dependency.
- **Phase 2 Foundation** depends on Phase 1 and blocks runtime implementation.
- **US1** depends on Phase 2 and is the recommended MVP because US2-US4 emit
  actionable reminders and completion events.
- **US2** depends on Phase 2 for core execution and on T032 for linked
  notification completion; its lifecycle tests remain runnable with a fake
  outcome resolver.
- **US3** depends on Phase 2 for core reporting and on T032 for actionable
  submission/review outcomes; milestone/risk sources are optional and empty-safe.
- **US4** depends on Phase 2 for core governance and on T032 for escalation
  outcomes; links to US2/US3 records are optional and permission-checked.
- **Phase 7** depends on every story selected for the release.

### User Story Dependency Graph

```text
Phase 1 Setup
  -> Phase 2 Foundation
      -> US1 Notification Loop (recommended MVP)
          ├── US2 Milestones and Deliverables
          ├── US3 Structured Reports and Analytics
          └── US4 Decisions and Risks

US2 + US3 + US4 -> Phase 7 Integrated Release Readiness
```

After US1, US2-US4 can proceed in parallel when multiple developers are
available. For the current solo-maintainer workflow, execute them sequentially
in the listed order to minimize file conflicts in shared event, notification,
locale, and project route files.

### Within Each Story

1. Complete all story test tasks and observe failures for missing behavior.
2. Add models and additive migrations.
3. Implement domain services and transactions.
4. Implement serializers/views/routes and make contract tests pass.
5. Add audit, notification, event, calendar, and operations integration.
6. Add typed frontend clients before screen components.
7. Add locale/accessibility/responsive behavior.
8. Run the independent checkpoint before starting the next story.

## Parallel Opportunities

- Setup T001-T005 can run in parallel; T006 follows the final artifact list.
- Foundation tests T007-T011 can run in parallel. T013-T014 can run in parallel
  after their tests; T015-T018 own separate modules.
- US1 tests T019-T027 can run in parallel. Models/migration are sequential;
  policy service T031 and frontend API T037 can proceed separately after shapes
  stabilize.
- US2 tests T043-T052 can run in parallel. Projects schema T053-T054 and
  submissions review-target schema T055 can be owned separately.
- US3 tests T073-T082 can run in parallel. Analytics/export and frontend
  template shell can split after the response contract is fixed.
- US4 tests T103-T111 can run in parallel. Decision UI and risk UI can split
  after T121.
- Cross-cutting T127-T130 can run in parallel before T131-T140.

## Parallel Examples

### User Story 1

```text
Task T019: Notification outcome unit tests
Task T022: Actionable notification API contract tests
Task T025: Notification isolation/security tests
Task T026: Notification drawer/preferences component tests
```

### User Story 2

```text
Task T043: Milestone derivation unit tests
Task T045: Reviewer authority unit tests
Task T049: Execution role/security matrix
Task T051: Execution workspace component tests
```

### User Story 3

```text
Task T073: Report template field tests
Task T076: Independent analytics fixtures
Task T079: Legacy migration tests
Task T081: Reports workspace component tests
```

### User Story 4

```text
Task T103: Decision immutability tests
Task T104: Nine-cell risk matrix tests
Task T109: Governance role/link security tests
Task T110: Decision/risk component tests
```

## Implementation Strategy

### MVP First

1. Complete T001-T006.
2. Complete T007-T018.
3. Complete US1 T019-T042.
4. Stop and validate notification delivery/read/acknowledgement/action,
   preferences, policy, retries, escalation, privacy, locale, and degradation.
5. Do not deploy while feature 017 acceptance remains Pending.

### Incremental Solo Delivery

1. **Foundation + US1**: establish reliable notification follow-through.
2. **US2**: add project outcome planning and evidence acceptance.
3. **US3**: standardize reports and expose explainable trends.
4. **US4**: preserve decisions and manage risks.
5. **Phase 7**: validate integrated security, migration, performance,
   accessibility, operations, and current-revision acceptance.

### Commit and Checkpoint Discipline

- Use feature branch `spec/feature-017` when repository workflow permits.
- Keep each task or tightly coupled task pair in a reviewable commit using the
  constitution format `[017] 描述变更内容`.
- Do not mark a task complete until its self-check passes.
- Stop at each story checkpoint; failures in an earlier story are fixed before
  proceeding to the next sequential increment.
