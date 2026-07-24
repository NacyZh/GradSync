---

description: "Implementation tasks for account security, project collaboration, audit operations, and release acceptance governance"
---

# Tasks: Access and Release Governance

**Input**: Design documents from `/specs/016-access-governance/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `contracts/frontend-ui.md`,
`contracts/acceptance.schema.json`, `quickstart.md`

**Tests**: TDD is mandatory under the GradSync constitution. Tests in each story
must be written and observed failing for missing behavior before its
implementation tasks begin. No test exception is approved in `plan.md`.

**Organization**: Tasks are grouped by independently testable user story. Every
task is scoped to eight hours or less and includes a concrete self-check.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish configuration, fixtures, and contract registration needed
by the four stories without changing business behavior.

- [X] T001 [P] [Ops] Add recovery TTL/throttling, approved frontend origin, audit retention/export, and export-expiry defaults to `.env.example` and `.env.production.example`; self-check: production examples contain no usable secret or unsafe wildcard origin (AC: plan security/operations gate)
- [X] T002 [P] [Backend] Add typed environment parsing and unsafe-production validation for feature settings in `backend/gradsync/settings/base.py` and `backend/gradsync/settings/production.py`; self-check: invalid TTL, row limit, retention floor, and origin values fail with actionable configuration errors (AC: OPS-007)
- [X] T003 [P] [Test] Extend reusable account/project fixtures for verified approved teachers, restricted accounts, collaborator roles, and administrators in `backend/tests/factories/accounts.py` and `backend/tests/factories/collaboration.py`; self-check: fixtures create every role/state without production resources (AC: AC-006, AC-008)
- [X] T004 [P] [Test] Extend Playwright API mocks and test identities for recovery, session, collaborator, reviewer, audit, and governance states in `frontend/tests/e2e/api-mocks.ts`; self-check: fixtures expose deterministic English/Chinese and role variants without weakening default denial (AC: AC-019)
- [X] T005 [P] [Docs] Register the 016 OpenAPI and acceptance contracts in `scripts/check-generated-artifacts.sh`; self-check: deleting either tracked contract makes the generated-artifact check fail (AC: constitution artifact gate)
- [X] T006 [Docs] Document feature configuration and focused validation commands in `README.md` and `docs/production.md`; self-check: commands match `specs/016-access-governance/quickstart.md` and use repository-relative paths (AC: OPS-003, OPS-007)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Provide correlation, immutable redacted evidence, and atomic
privileged mutation primitives shared by US1-US3.

**CRITICAL**: Complete this phase before runtime user-story implementation.

### Foundational Tests

- [X] T007 [P] [Test] Add unit tests for audit allowlist snapshots and recursive secret redaction in `backend/tests/unit/test_audit_redaction.py`; self-check: passwords, tokens, cookies, authorization values, private bodies, and uploaded bytes fail before implementation (AC: AC-012)
- [X] T008 [P] [Test] Add integration tests for request correlation propagation and immutable audit fields in `backend/tests/integration/test_audit_evidence.py`; self-check: API response, structured log, and audit event share one correlation ID and ordinary update/delete is rejected (AC: AC-015)
- [X] T009 [P] [Test] Add integration tests proving privileged domain writes roll back when required audit persistence fails in `backend/tests/integration/test_audit_atomicity.py`; self-check: domain rows remain unchanged for simulated audit failures (AC: AC-015)
- [X] T010 [P] [Test] Add migration preservation and application-rollback compatibility tests for existing audit rows and actor/target snapshots in `backend/tests/integration/test_access_governance_migrations.py`; self-check: pre-migration evidence remains readable after forward migration and old application code can run while the additive schema stays applied (AC: OPS-003, OPS-004)

### Foundational Implementation

- [X] T011 [Backend] Add category, outcome, reason, correlation ID, actor snapshot, redaction version, and supporting indexes to `backend/apps/audit/models.py`; self-check: model constraints preserve append-only evidence and bounded indexed filtering (AC: AC-011, AC-012)
- [X] T012 [Backend] Create the additive audit schema migration in `backend/apps/audit/migrations/0005_access_governance_evidence.py`; self-check: forward migration preserves existing rows and the migration is retained during application rollback so evidence is not deleted (AC: OPS-003, OPS-004)
- [X] T013 [Backend] Implement write-time allowlist serialization and recursive redaction in `backend/apps/audit/services.py`; self-check: T007 passes and no secret is retained for later client-side masking (AC: AC-012)
- [X] T014 [Backend] Add request correlation extraction/generation to `backend/apps/common/middleware.py`; self-check: trusted incoming IDs are normalized, invalid IDs are replaced, and response headers expose the effective ID (AC: AC-015)
- [X] T015 [Backend] Add an atomic privileged-mutation helper that persists required audit evidence in the same transaction in `backend/apps/audit/services.py`; self-check: T009 passes without swallowing persistence failures (AC: AC-015)
- [X] T016 [Backend] Extend safe audit serialization without mutation endpoints in `backend/apps/audit/serializers.py`; self-check: existing audit consumers remain compatible and new snapshots never include redacted source fields (AC: AC-012)
- [X] T017 [Ops] Add audit write failure and correlation signals to `backend/apps/common/production_checks.py` and `backend/apps/common/management/commands/check_production_readiness.py`; self-check: simulated required-audit unavailability fails readiness with no secret output (AC: OPS-002, OPS-007)

**Checkpoint**: Shared accountability writes are atomic, redacted, correlated,
and migration-safe.

---

## Phase 3: User Story 1 - Recover and Secure an Account (Priority: P1) MVP

**Goal**: Deliver enumeration-resistant password recovery, verified email
change, authoritative browser/JWT session inventory, and immediate revocation
without changing account status or role activation.

**Independent Test**: Exercise recovery, email change, session listing, one
session revocation, and all-other-session revocation across active, suspended,
archived, pending-email, and pending-role accounts; only eligible users regain
sign-in, every prior session is revoked after reset, and restrictions remain.

### Tests for User Story 1

- [X] T018 [P] [US1] [Test] Add model/state-machine tests for hashed recovery and email-change requests in `backend/tests/unit/test_account_security_lifecycle.py`; self-check: expiry, supersession, cancellation, one-use, purpose binding, and hash-only storage fail before implementation (AC: AC-003, AC-004)
- [X] T019 [P] [US1] [Test] Add contract tests for password recovery and confirmation endpoints in `backend/tests/contract/test_account_security_api.py`; self-check: public responses are identical for eligible, unknown, suspended, and archived addresses (AC: AC-001, AC-002)
- [X] T020 [P] [US1] [Test] Add contract tests for email-change request/status/verify/resend/cancel endpoints in `backend/tests/contract/test_account_security_api.py`; self-check: current-password, uniqueness, pending-authority, expiry, and localized error codes are covered (AC: AC-004, AC-006)
- [X] T021 [P] [US1] [Test] Add contract tests for session list, single revoke, and revoke-others endpoints in `backend/tests/contract/test_account_sessions_api.py`; self-check: responses expose recognizable metadata and never credentials (AC: AC-005)
- [X] T022 [P] [US1] [Test] Add concurrency and replay integration tests for reset, email uniqueness, and session revocation in `backend/tests/integration/test_account_security_concurrency.py`; self-check: exactly one stale competing mutation succeeds (AC: AC-003, AC-004)
- [X] T023 [P] [US1] [Test] Add dual Django-session/JWT revocation and legacy token tests in `backend/tests/integration/test_account_session_enforcement.py`; self-check: revoked sessions fail on the next request and refresh tokens without `sid` cannot rotate (AC: AC-001, AC-005)
- [X] T024 [P] [US1] [Test] Add component tests for forgot/reset pages and profile security controls in `frontend/tests/component/account-security.test.tsx`; self-check: generic acknowledgement, invalid-link, pending-email, confirmation, toast, focus, and both locales fail before UI implementation (AC: AC-019)
- [X] T025 [P] [US1] [Test] Add full-stack recovery and session lifecycle journeys in `frontend/tests/e2e/account-security.spec.ts`; self-check: workflows complete at 390px, 900px, and 1440px without overlap or embedded transient status (AC: AC-001, AC-005, AC-019)

### Implementation for User Story 1

- [X] T026 [P] [US1] [Backend] Add `AccountRecoveryRequest`, `EmailChangeRequest`, and `AccountSession` entities and constraints to `backend/apps/accounts/models.py`; self-check: only hashes are stored and one current request/session identity is enforceable (AC: AC-003, AC-005)
- [X] T027 [US1] [Backend] Create account security/session tables and indexes in `backend/apps/accounts/migrations/0007_access_security_lifecycle.py`; self-check: migration preserves existing account status, email verification, locale, and role activation data (AC: AC-006, OPS-003)
- [X] T028 [US1] [Backend] Implement token issue, supersession, validation, consumption, and reset locking in `backend/apps/accounts/security_services.py`; self-check: T018 and T022 recovery cases pass with a 30-minute default (AC: AC-001, AC-003)
- [X] T029 [US1] [Backend] Implement current-password-confirmed email change, verification, cancellation, resend, and uniqueness locking in `backend/apps/accounts/security_services.py`; self-check: old email remains authoritative until one successful atomic verification (AC: AC-004, AC-006)
- [X] T030 [US1] [Backend] Implement session creation, activity update, individual revocation, revoke-others, and revoke-all in `backend/apps/accounts/session_services.py`; self-check: current-session preservation and idempotent revocation rules pass (AC: AC-005)
- [X] T031 [US1] [Backend] Bind `sid` to access/refresh token families and reject legacy unbound refresh rotation in `backend/apps/accounts/tokens.py`; self-check: existing short-lived access compatibility remains until expiry and T023 passes (AC: AC-005)
- [X] T032 [US1] [Backend] Enforce authoritative session/account state for Django and JWT protected requests in `backend/apps/accounts/authentication.py`; self-check: suspended, archived, unverified, pending-role, and revoked contexts fail on the next request (AC: AC-005, AC-006)
- [X] T033 [US1] [Backend] Add recovery, email-change, and session request/response serializers with stable error codes in `backend/apps/accounts/serializers.py`; self-check: serializers conform to `contracts/openapi.yaml` and never echo secrets (AC: AC-002, AC-004)
- [X] T034 [US1] [Backend] Add public recovery and authenticated security views with scoped throttling, CSRF, and approved-origin enforcement in `backend/apps/accounts/views.py`; self-check: unsafe redirects and enumeration probes receive no account metadata (AC: AC-002, AC-003)
- [X] T035 [US1] [Backend] Register account security/session routes and OpenAPI annotations in `backend/apps/accounts/urls.py` and `backend/apps/accounts/schema.py`; self-check: all US1 contract operations appear in generated schema with expected statuses (AC: AC-001, AC-005)
- [X] T036 [US1] [Backend] Integrate recovery, email-change, and session security notices with delivery outcomes in `backend/apps/accounts/services.py`; self-check: old/new recipients follow FR-009 and delivery errors expose retry state without token content (AC: AC-004, OPS-001)
- [X] T037 [US1] [Backend] Record redacted issuance/completion/cancellation/revocation evidence through `backend/apps/audit/services.py`; self-check: each successful governed mutation has actor/context/outcome while unknown-email requests remain non-enumerable (AC: AC-012, AC-015)
- [X] T038 [P] [US1] [Frontend] Add typed recovery, email-change, and session API clients in `frontend/src/features/auth/api.ts`; self-check: clients use stable error codes and clear private query caches on authentication loss (AC: AC-005)
- [X] T039 [P] [US1] [Frontend] Build public recovery request and reset experiences in `frontend/src/features/auth/ForgotPasswordPage.tsx` and `frontend/src/features/auth/ResetPasswordPage.tsx`; self-check: generic completion and invalid-link states satisfy the UI contract by keyboard (AC: AC-001, AC-002, AC-019)
- [X] T040 [US1] [Frontend] Build email-change and bounded active-session controls in `frontend/src/features/auth/SecuritySettingsPanel.tsx` and integrate them in `frontend/src/features/auth/ProfilePage.tsx`; self-check: revocation takes at most three interactions and uses global toast (AC: AC-004, AC-005)
- [X] T041 [US1] [Frontend] Register public routes and authentication-boundary invalidation in `frontend/src/routes/index.tsx` and `frontend/src/features/auth/AuthProvider.tsx`; self-check: recovery works before login and revoked current contexts return to sign-in without private cache leakage (AC: AC-005)
- [X] T042 [US1] [Frontend] Add complete English/Chinese account-security strings and notification mappings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: i18n completeness tests report no fallback or raw backend message (AC: AC-019)
- [X] T043 [US1] [Test] Add a 10,000-account/session performance test in `backend/tests/integration/test_account_security_performance.py`; self-check: p95 acknowledgement/session inventory stays below two seconds and pages remain bounded (AC: AC-001, PERF-001)
- [X] T044 [US1] [Ops] Add recovery throttle, delivery failure, and session revocation counters/readiness to `backend/apps/common/production_checks.py` and `docs/ops/monitoring-alerts.md`; self-check: operators can distinguish abuse, delivery, and revocation failures without seeing addresses or secrets (AC: OPS-001, OPS-002)

**Checkpoint**: US1 is deployable and independently demonstrable as the MVP.

---

## Phase 4: User Story 2 - Govern Project Collaborator Roles (Priority: P1)

**Goal**: Complete one-primary-advisor, co-advisor, reviewer, observer, student,
and global-administrator boundaries with target-specific review assignments,
ownership transfer, governance hold, notifications, and immediate enforcement.

**Independent Test**: Populate two unrelated projects with every role, exercise
all reads/writes, change/remove roles, assign review targets, transfer ownership,
and trigger/resolve a governance hold; forbidden actions and stale URLs disclose
no hidden metadata on the next request.

### Tests for User Story 2

- [X] T045 [P] [US2] [Test] Add exhaustive project capability matrix tests in `backend/tests/unit/test_project_access_capabilities.py`; self-check: every allowed and denied role/action pair from the UI contract is asserted before implementation (AC: AC-008)
- [X] T046 [P] [US2] [Test] Add collaborator eligibility, one-role, and duplicate/concurrent membership tests in `backend/tests/unit/test_project_collaboration_rules.py`; self-check: students, admins, inactive, unverified, and unapproved teachers are excluded (AC: AC-007, AC-009)
- [X] T047 [P] [US2] [Test] Add member search/change/remove/transfer/hold contract tests in `backend/tests/contract/test_access_governance_projects_api.py`; self-check: administrator reason and capability payload requirements match OpenAPI (AC: AC-007, AC-009)
- [X] T048 [P] [US2] [Test] Add target-specific reviewer assignment contract tests in `backend/tests/contract/test_review_assignments_api.py`; self-check: one-target validation and reviewer assignment/revocation statuses fail before implementation (AC: AC-008, AC-010)
- [X] T049 [P] [US2] [Test] Add authorization and stale-link isolation tests across project/task/material/report/writing/comment endpoints in `backend/tests/integration/test_project_collaborator_security.py`; self-check: forbidden responses reveal no project or target metadata (AC: AC-008, AC-010)
- [X] T050 [P] [US2] [Test] Add ownership transfer, external ineligibility, governance-hold, and concurrent role mutation tests in `backend/tests/integration/test_project_governance_lifecycle.py`; self-check: exactly one eligible primary advisor remains or the project is held (AC: AC-009)
- [X] T051 [P] [US2] [Test] Add forward-migration tests for teacher-owned, admin-owned, ineligible-owned, duplicate-advisor, and student membership fixtures in `backend/tests/integration/test_project_governance_migration.py`; self-check: valid students/data remain unchanged and problematic projects are reported held (AC: OPS-003, OPS-005)
- [X] T052 [P] [US2] [Test] Add collaborator selector, capability-safe navigation, hold banner, and reviewer assignment component tests in `frontend/tests/component/project-governance.test.tsx`; self-check: forbidden controls are absent and account options appear only after search (AC: AC-007, AC-019)
- [X] T053 [P] [US2] [Test] Add full-stack role matrix, transfer, hold resolution, and stale-link journeys in `frontend/tests/e2e/project-governance.spec.ts`; self-check: all roles work in both locales at 390px and 1440px without metadata leakage (AC: AC-008, AC-010, AC-019)

### Implementation for User Story 2

- [X] T054 [P] [US2] [Backend] Add project governance fields, `co_advisor` membership role, active-history metadata, and one-role constraints in `backend/apps/projects/models.py`; self-check: primary ownership remains canonical in `ResearchProject.advisor` and admins cannot be members (AC: AC-007, AC-009)
- [X] T055 [P] [US2] [Backend] Add explicit target-specific `SubmissionReviewAssignment` constraints and indexes in `backend/apps/submissions/models.py`; self-check: exactly one weekly-report/writing-version/legacy target is set and duplicates are prevented (AC: AC-008)
- [X] T056 [US2] [Backend] Create project governance schema/data migration in `backend/apps/projects/migrations/0003_access_governance_roles.py`; self-check: eligible owners map to primary membership and admin/ineligible ownership enters a reasoned hold (AC: OPS-003, OPS-005)
- [X] T057 [US2] [Backend] Create reviewer assignment schema migration in `backend/apps/submissions/migrations/0007_review_assignments.py`; self-check: existing submissions and writing participants remain readable (AC: OPS-003)
- [X] T058 [US2] [Backend] Implement centralized role/capability and governance-hold evaluation in `backend/apps/projects/access_services.py`; self-check: T045 passes with per-request account/membership/assignment evaluation and no cache authority (AC: AC-008, AC-010)
- [X] T059 [US2] [Backend] Implement bounded eligible-teacher search and collaborator add/change/remove locking in `backend/apps/projects/collaboration_services.py`; self-check: results cap at 25 and concurrent writes cannot create duplicate active roles (AC: AC-007, PERF-003)
- [X] T060 [US2] [Backend] Implement sole-owner transfer, former-owner disposition, automatic hold, and administrator hold resolution in `backend/apps/projects/collaboration_services.py`; self-check: no voluntary owner removal succeeds without an eligible successor (AC: AC-009)
- [X] T061 [US2] [Backend] Implement assignment creation/removal and target access evaluation in `backend/apps/submissions/review_assignment_services.py`; self-check: reviewers access only assigned target history/comments and lose access immediately on removal (AC: AC-008, AC-010)
- [X] T062 [US2] [Backend] Replace scattered project role checks with centralized capabilities in `backend/apps/projects/permissions.py` and `backend/apps/projects/services.py`; self-check: admin supervision does not grant creation, ownership, membership, or ordinary project mutation (AC: AC-008)
- [X] T063 [US2] [Backend] Apply capability checks to task and material operations in `backend/apps/tasks/services.py`, `backend/apps/tasks/views.py`, and `backend/apps/projects/material_services.py`; self-check: reviewer/observer reads and all mutation boundaries match the role matrix (AC: AC-008)
- [X] T064 [US2] [Backend] Apply assignment-aware capability checks to report, writing, review, and comment operations in `backend/apps/submissions/permissions.py`, `backend/apps/submissions/report_services.py`, `backend/apps/submissions/writing_services.py`, and `backend/apps/submissions/comment_services.py`; self-check: unassigned target enumeration and inline comments are denied (AC: AC-008, AC-010)
- [X] T065 [US2] [Backend] Add collaborator, transfer, governance-hold, and assignment serializers/views/routes in `backend/apps/projects/serializers.py`, `backend/apps/projects/views.py`, `backend/apps/projects/urls.py`, `backend/apps/submissions/serializers.py`, `backend/apps/submissions/views.py`, and `backend/apps/submissions/urls.py`; self-check: generated operations cover all US2 OpenAPI paths (AC: AC-007, AC-009)
- [X] T066 [US2] [Backend] Emit project live events and affected-user notifications for assignment, role change/removal, transfer, hold, and resolution in `backend/apps/projects/services.py`; self-check: delivery failures are retryable and do not expose project-private data (AC: AC-007, OPS-001)
- [X] T067 [US2] [Backend] Wrap collaborator/ownership/assignment changes in atomic audit writes in `backend/apps/projects/collaboration_services.py` and `backend/apps/submissions/review_assignment_services.py`; self-check: administrator interventions require a reason and failed evidence rolls back mutation (AC: AC-015)
- [X] T068 [P] [US2] [Frontend] Add typed collaborator, capability, transfer, hold, and review-assignment clients in `frontend/src/features/projects/api.ts`, `frontend/src/features/projects/index.ts`, and `frontend/src/features/submissions/api.ts`; self-check: submissions imports only the projects public API and passes import-boundary tests (AC: AC-007)
- [X] T069 [P] [US2] [Frontend] Build input-driven eligible-teacher combobox with role/multi-select support in `frontend/src/features/projects/TeacherSelector.tsx`; self-check: no unrestricted list renders, selection is keyboard-operable, and 25-result bounds are preserved (AC: AC-007, AC-019)
- [X] T070 [US2] [Frontend] Refactor fixed-height collaborator management and ownership controls in `frontend/src/features/projects/ProjectCollaboratorsPanel.tsx` and `frontend/src/features/projects/ProjectMembersPanel.tsx`; self-check: controls follow effective capabilities and mutations use global toast (AC: AC-007, AC-019)
- [X] T071 [US2] [Frontend] Integrate role-aware project navigation, actions, and governance-hold banner in `frontend/src/features/projects/ProjectDashboardPage.tsx`, `frontend/src/features/projects/ProjectContextBanner.tsx`, and `frontend/src/features/projects/ProjectsLandingPage.tsx`; self-check: observer/reviewer/student/admin controls differ exactly as contracted (AC: AC-008, AC-010)
- [X] T072 [US2] [Frontend] Add target-specific reviewer assignment control to `frontend/src/features/submissions/ReviewerAssignmentControl.tsx` and connect it to `frontend/src/features/submissions/ReviewQueuePage.tsx` and `frontend/src/features/submissions/InlineCommentPanel.tsx`; self-check: selected target, revision history, and inline comment context stay synchronized (AC: AC-008)
- [X] T073 [US2] [Frontend] Invalidate collaborator, navigation, submission, and member queries from project events in `frontend/src/features/projects/useProjectLiveRefresh.ts`; self-check: changed/removed roles update without full reload and next forbidden action redirects safely (AC: AC-010, PERF-005)
- [X] T074 [US2] [Frontend] Add complete English/Chinese collaborator, role, hold, transfer, reviewer, notification, and toast strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: no untranslated enum or raw API error appears (AC: AC-019)
- [X] T075 [US2] [Ops] Add held-project report/readiness and role-conflict signals to `backend/apps/common/production_checks.py` and `docs/ops/monitoring-alerts.md`; self-check: operators can identify held project IDs/reasons without member-private payloads (AC: OPS-002, OPS-005, OPS-007)

**Checkpoint**: US2 enforces complete project collaboration independently of
the audit console and release checker.

---

## Phase 5: User Story 3 - Investigate Activity in an Audit Console (Priority: P1)

**Goal**: Give administrators a safe, self-auditing, filterable audit console
with immutable detail and bounded asynchronous CSV exports.

**Independent Test**: Seed 100,000 varied events, filter and inspect them as an
administrator, export the exact authorized scope, and verify ordering,
pagination, redaction, self-auditing, authorization, expiry, and performance.

### Tests for User Story 3

- [X] T076 [P] [US3] [Test] Add cursor/filter/detail/export API contract tests in `backend/tests/contract/test_audit_console_api.py`; self-check: parameters, capability payloads, statuses, limits, and download authorization match OpenAPI (AC: AC-011, AC-013)
- [X] T077 [P] [US3] [Test] Add audit filter ordering, combined scope, and self-auditing integration tests in `backend/tests/integration/test_audit_console.py`; self-check: searches/details/exports create evidence without recursively exposing or duplicating results (AC: AC-011, AC-015)
- [X] T078 [P] [US3] [Test] Add non-admin denial and redaction regression tests in `backend/tests/integration/test_audit_console_security.py`; self-check: users receive no counts, suggestions, rows, detail, export state, file body, or secret value (AC: AC-012, AC-014)
- [X] T079 [P] [US3] [Test] Add 100,000-row filter and 10,000-row export performance tests in `backend/tests/integration/test_audit_console_performance.py`; self-check: p95 pages stay below two seconds and exports finish below 60 seconds without unbounded transactions (AC: AC-011, AC-013)
- [X] T080 [P] [US3] [Test] Add Celery export retry, expiry, high-water mark, and idempotency tests in `backend/tests/integration/test_audit_exports.py`; self-check: retries cannot widen scope or duplicate a ready artifact (AC: AC-013)
- [X] T081 [P] [US3] [Test] Add audit list/detail/filter/export component tests in `frontend/tests/component/audit-console.test.tsx`; self-check: bounded list, separate detail, URL filters, state handling, toasts, keyboard use, and both locales fail before implementation (AC: AC-019)
- [X] T082 [P] [US3] [Test] Add administrator and non-administrator full-stack audit journeys in `frontend/tests/e2e/audit-console.spec.ts`; self-check: 390px uses a half-screen detail sheet and 1440px uses aligned list/detail with no overflow (AC: AC-014, AC-019)

### Implementation for User Story 3

- [X] T083 [P] [US3] [Backend] Add `AuditExport` lifecycle, immutable filter snapshot, high-water event ID, expiry, and indexes in `backend/apps/audit/models.py`; self-check: maximum row count is constrained and event rows remain append-only (AC: AC-013)
- [X] T084 [US3] [Backend] Create audit export schema/index migration in `backend/apps/audit/migrations/0006_audit_exports.py`; self-check: existing 100,000-row audit fixtures migrate without rewrite or loss (AC: AC-011, OPS-003)
- [X] T085 [US3] [Backend] Implement stable newest-first cursor pagination and normalized combined filters in `backend/apps/audit/views.py` and `backend/apps/common/pagination.py`; self-check: no offset drift occurs when newer events arrive (AC: AC-011)
- [X] T086 [US3] [Backend] Implement immutable authorized filter snapshots and bounded CSV chunk generation in `backend/apps/audit/export_services.py`; self-check: exported IDs equal the requested high-water scope and rows never exceed 10,000 (AC: AC-012, AC-013)
- [X] T087 [US3] [Backend] Add idempotent Celery generation, retry, expiry, and cleanup tasks in `backend/apps/audit/tasks.py`; self-check: queued status appears within two seconds and failed jobs expose a safe retry reason (AC: AC-013, PERF-004)
- [X] T088 [US3] [Backend] Add administrator-only audit list/detail/export/status/download serializers and views in `backend/apps/audit/serializers.py` and `backend/apps/audit/views.py`; self-check: request-time authorization applies to every operation and download uses existing safe helpers (AC: AC-014)
- [X] T089 [US3] [Backend] Register audit console/export routes in `backend/apps/audit/urls.py`; self-check: generated schema covers all US3 contract operations and exposes no mutation of event rows (AC: AC-011, AC-014)
- [X] T090 [US3] [Backend] Record audit search, detail, export request, completion, failure, and download evidence in `backend/apps/audit/services.py` and `backend/apps/audit/tasks.py`; self-check: evidence identifies requester/scope/outcome without including CSV bodies (AC: AC-015)
- [X] T091 [P] [US3] [Frontend] Add typed cursor-filter/detail/export clients in `frontend/src/features/admin/api.ts`; self-check: query keys include normalized URL filters and downloads require server capability (AC: AC-011, AC-013)
- [X] T092 [US3] [Frontend] Build responsive filter band, bounded event list, and detail workspace in `frontend/src/features/admin/AuditConsolePage.tsx` and `frontend/src/features/admin/AuditEventDetail.tsx`; self-check: loading/empty/filtered-empty/unavailable/redacted states keep stable dimensions (AC: AC-019)
- [X] T093 [US3] [Frontend] Add export status, retry, expiry, and download controls to `frontend/src/features/admin/AuditConsolePage.tsx`; self-check: global toast reports mutations and expired/unauthorized controls are absent (AC: AC-013, AC-019)
- [X] T094 [US3] [Frontend] Register administrator-only navigation/route and safe responsive sheet behavior in `frontend/src/app/Layout.tsx` and `frontend/src/routes/index.tsx`; self-check: non-admin navigation and direct routes disclose no audit metadata (AC: AC-014)
- [X] T095 [US3] [Frontend] Add complete English/Chinese audit filter, detail, state, export, and toast strings in `frontend/src/data/locale/messages.en.ts` and `frontend/src/data/locale/messages.zh.ts`; self-check: i18n completeness detects no fallback keys (AC: AC-019)
- [X] T096 [US3] [Ops] Add export queue age/failure/expiry readiness signals and runbook guidance in `backend/apps/common/production_checks.py` and `docs/ops/monitoring-alerts.md`; self-check: ordinary application reads remain available while export degradation is visible (AC: OPS-002, OPS-007, OPS-008)

**Checkpoint**: US3 can be tested with seeded evidence regardless of whether
release acceptance enforcement is enabled.

---

## Phase 6: User Story 4 - Enforce Specification Acceptance (Priority: P1)

**Goal**: Deterministically bind separate Product, Testing, and Development
decisions to normative specification content and block production release when
evidence is pending, rejected, stale, malformed, or not exactly covered by a
valid exception.

**Independent Test**: Evaluate accepted, pending, rejected, materially changed,
format-only changed, valid-exception, and every invalid-exception fixture from a
clean checkout; diagnostics identify blockers and production enforcement fails
closed before image publication.

### Tests for User Story 4

- [X] T097 [P] [US4] [Test] Add acceptance JSON schema fixture tests in `scripts/tests/test_check_spec_acceptance.py` and `scripts/tests/fixtures/spec-acceptance/`; self-check: malformed decisions and exceptions are rejected against `contracts/acceptance.schema.json` (AC: AC-016, AC-018)
- [X] T098 [P] [US4] [Test] Add normative fingerprint tests for user stories, boundaries, ACs, included/unsupported scope, and requirements in `scripts/tests/test_check_spec_acceptance.py`; self-check: material edits stale decisions while formatting/metadata/explanatory edits retain the hash (AC: AC-017)
- [X] T099 [P] [US4] [Test] Add decision-state and multi-discipline reviewer tests in `scripts/tests/test_check_spec_acceptance.py`; self-check: disciplines remain separate and pending/rejected/stale blockers are all reported (AC: AC-016)
- [X] T100 [P] [US4] [Test] Add exception owner/approver, scope, revision, approval, revocation, and 14-day expiry tests in `scripts/tests/test_check_spec_acceptance.py`; self-check: no invalid or over-broad exception permits release (AC: AC-018)
- [X] T101 [P] [US4] [Test] Add clean-checkout discovery and legacy-spec pending migration tests in `scripts/tests/test_check_spec_acceptance.py`; self-check: every tracked feature is evaluated and missing structured evidence defaults to pending (AC: AC-016, OPS-006)
- [X] T102 [P] [US4] [Test] Add CI workflow ordering tests in `scripts/tests/test_release_acceptance_gate.py`; self-check: production image and deployment jobs cannot run before acceptance enforcement succeeds (AC: AC-016)

### Implementation for User Story 4

- [X] T103 [P] [US4] [CI] Add repository acceptance policy with required disciplines, normative headings, exception lifetime, and release scopes in `.specify/acceptance-policy.json`; self-check: policy has no environment-specific identity or mutable production state (AC: AC-016, AC-017)
- [X] T104 [P] [US4] [Docs] Add pending current-revision evidence for feature 016 in `specs/016-access-governance/acceptance.json`; self-check: file validates against `contracts/acceptance.schema.json` and does not falsely mark any reviewer accepted (AC: AC-016)
- [X] T105 [US4] [CI] Implement deterministic Markdown normative-section extraction and SHA-256 fingerprinting in `scripts/check-spec-acceptance.py`; self-check: T098 passes using only Python standard library (AC: AC-017)
- [X] T106 [US4] [CI] Implement acceptance schema validation and separate decision evaluation in `scripts/check-spec-acceptance.py`; self-check: pending/rejected/stale/malformed evidence fails closed with discipline-specific reasons (AC: AC-016)
- [X] T107 [US4] [CI] Implement exact-scope, revision-bound, distinct-approver, revocable, maximum-14-day exception evaluation in `scripts/check-spec-acceptance.py`; self-check: T100 passes and owner cannot approve their own exception (AC: AC-018)
- [X] T108 [US4] [CI] Implement repository feature discovery, legacy pending defaults, report mode, enforce mode, and machine-readable output in `scripts/check-spec-acceptance.py`; self-check: clean checkout evaluation completes under two seconds and identifies every blocker (AC: AC-016, OPS-006)
- [X] T109 [US4] [CI] Add acceptance schema/policy/evidence checks to `scripts/check-generated-artifacts.sh`; self-check: missing, malformed, or untracked governance evidence blocks generated-artifact validation (AC: AC-016)
- [X] T110 [US4] [CI] Add diagnostic acceptance reporting to backend/frontend CI and mandatory production enforcement before image build in `.github/workflows/release.yml`; self-check: pull requests report blockers while production image/deploy needs the enforce job (AC: AC-016)
- [X] T111 [US4] [Ops] Add release eligibility enforcement and non-secret remediation output to `scripts/check-production-readiness.sh` and `scripts/deploy-production.sh`; self-check: unavailable evidence aborts before migration/image deployment and never mutates acceptance files (AC: AC-016, OPS-007)
- [X] T112 [US4] [Ops] Emit structured release evaluation evidence to CI artifacts/logs in `scripts/check-spec-acceptance.py`; self-check: revision, decisions, exception ID/scope/expiry, blockers, time, and outcome are attributable without credentials (AC: AC-015)
- [X] T113 [US4] [Docs] Document reviewer assignment, decision updates, stale refresh, exception approval, and remediation workflow in `docs/production.md`; self-check: one account may review multiple disciplines but each decision remains explicit (AC: AC-016, AC-018)
- [X] T114 [US4] [Docs] Update the current feature review block and acceptance instructions in `specs/016-access-governance/spec.md` without changing decisions from Pending; self-check: normative revision and structured evidence agree after documentation update (AC: AC-017)

**Checkpoint**: US4 deterministically governs release from repository evidence
and does not depend on the production database or application UI.

---

## Phase 7: Polish & Cross-Cutting Release Readiness

**Purpose**: Validate integrated security, UX, migration, observability, and
release behavior after all desired stories are complete.

- [X] T115 [P] [Test] Extend OpenAPI operation/shape coverage for feature 016 in `backend/tests/contract/test_openapi_schema.py`; self-check: `scripts/check-openapi-contract.sh specs/016-access-governance/contracts/openapi.yaml` passes with strict shapes (AC: constitution contract gate)
- [X] T116 [P] [Test] Extend frontend private-import boundary rules for new auth/project/submission/admin modules in `frontend/tests/component/frontend-import-boundaries.test.ts`; self-check: cross-feature calls use public APIs and the boundary suite has zero violations (AC: plan layering gate)
- [X] T117 [P] [Test] Extend translation completeness and raw-message detection in `frontend/tests/component/i18n-completeness.test.ts`; self-check: every new API state, toast, confirmation, notification, and empty state switches fully between English and Chinese (AC: AC-019)
- [X] T118 [Test] Extend responsive overlap and keyboard coverage for all new workspaces in `frontend/tests/e2e/production-ui.spec.ts` and `frontend/tests/e2e/accessibility.spec.ts`; self-check: 390px, 900px, and 1440px have no clipped text, overlap, page overflow, or inaccessible controls (AC: AC-019)
- [X] T119 [Test] Run representative recovery, collaborator assignment, and audit investigation usability protocol and record anonymized results in `specs/016-access-governance/checklists/usability.md`; self-check: at least 90% complete one journey without administrator/developer help (AC: AC-020)
- [X] T120 [Ops] Add backup, migration dry-run, held-project report, legacy-session re-login, audit export retention, and evidence-preserving rollback steps to `docs/ops/backup-restore-drill.md` and `docs/production.md`; self-check: rollback never reactivates sessions/roles, clears holds, or discards evidence (AC: OPS-003, OPS-004, OPS-008)
- [X] T121 [CI] Run and document all commands from `specs/016-access-governance/quickstart.md`, including backend lint/tests/migrations, frontend lint/test/build/e2e, OpenAPI drift, generated artifacts, readiness, and acceptance enforcement; self-check: CI-equivalent checks pass with no generated files or unresolved warnings (AC: all release gates)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** has no dependencies.
- **Phase 2 Foundation** depends on Phase 1 and blocks runtime stories US1-US3.
- **US1** depends on Phase 2 and is the suggested MVP.
- **US2** depends on Phase 2. Its atomic evidence tasks use the foundational
  audit service, but it does not require US1 UI or account-recovery flows.
- **US3** depends on Phase 2. It may begin in parallel with US1/US2 once the
  additive audit foundation is stable.
- **US4** depends only on Phase 1 contracts/repository structure and may run in
  parallel with Phase 2 and all runtime stories.
- **Phase 7** depends on every story selected for the release.

### User Story Dependency Graph

```text
Phase 1 Setup
├── US4 Specification Acceptance
└── Phase 2 Audit/Correlation Foundation
    ├── US1 Account Security (MVP)
    ├── US2 Project Collaboration
    └── US3 Audit Console

US1 + US2 + US3 + US4 -> Phase 7 Release Readiness
```

### Within Each Story

1. Write the story's test tasks and confirm the missing behavior fails.
2. Add models and migrations before services.
3. Implement services before serializers/views/routes.
4. Apply authorization and atomic audit behavior before frontend integration.
5. Implement API clients before screens and route wiring.
6. Complete localization, performance, operations, and independent story tests.
7. Stop at the checkpoint until the story passes independently.

## Parallel Opportunities

- T001-T005 can proceed in parallel; T006 follows finalized configuration names.
- T007-T010 can proceed in parallel before T011-T017.
- US1 test tasks T018-T025 are parallel; backend model/service work and frontend
  skeleton work can split after contracts stabilize.
- US2 test tasks T045-T053 are parallel. Project schema T054/T056 and submission
  schema T055/T057 can be owned separately before access integration.
- US3 test tasks T076-T082 are parallel. Backend export work and frontend
  console work can split after API response shapes are fixed.
- US4 test tasks T097-T102 and policy/evidence tasks T103-T104 are parallel.
- US1, US2, US3, and US4 can be assigned to separate teams after their stated
  foundation dependencies are met.
- T115-T117 can run in parallel before integrated E2E and operations validation.

## Parallel Examples

### User Story 1

```text
Task T019: Recovery endpoint contract tests
Task T021: Session endpoint contract tests
Task T024: Account-security component tests
Task T025: Account-security Playwright journey
```

### User Story 2

```text
Task T045: Project capability matrix tests
Task T048: Review assignment contract tests
Task T051: Governance migration tests
Task T052: Project governance component tests
```

### User Story 3

```text
Task T076: Audit API contract tests
Task T078: Audit authorization/redaction tests
Task T079: Audit performance tests
Task T081: Audit console component tests
```

### User Story 4

```text
Task T097: Acceptance schema fixtures
Task T098: Normative fingerprint fixtures
Task T100: Exception governance fixtures
Task T102: Release workflow ordering tests
```

## Implementation Strategy

### MVP First

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete US1 through T044.
4. Stop and validate account recovery, email change, session inventory, and
   revocation independently.
5. Release US1 only if existing acceptance policy permits and all migration,
   readiness, security, locale, accessibility, and rollback checks pass.

### Incremental Delivery

1. **Foundation + US1**: restore self-service account access and session control.
2. **US2**: close project collaborator and review authorization boundaries.
3. **US3**: make existing and new governance evidence operationally usable.
4. **US4**: enforce specification acceptance before production artifacts.
5. **Phase 7**: validate the integrated release and operational procedures.

### Multi-Team Execution

- Team A owns US1 under `accounts` and frontend `auth`.
- Team B owns US2 under `projects`/`submissions` and project frontend modules.
- Team C owns US3 under `audit` and frontend `admin`.
- Team D owns US4 repository scripts, acceptance evidence, and release workflow.
- Shared changes to audit services, locale dictionaries, routing, and CI require
  review from the owning story teams before merge.
