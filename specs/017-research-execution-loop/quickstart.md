# Quickstart: Research Execution Loop

## Prerequisites

- Python 3.12 environment at `.venv` with backend development dependencies.
- Frontend dependencies installed under `frontend/`.
- PostgreSQL, Redis, Celery worker, and Celery Beat matching the existing
  development/CI profile.
- Active primary advisor, co-advisor, reviewer, observer, administrator, and at
  least two student accounts.
- Two unrelated projects with tasks, project materials, report schedules,
  historical weekly report revisions, and different memberships.
- Current feature acceptance remains a production release gate; test and
  planning work may run while decisions are Pending.

## Planned Configuration

Document safe defaults and enforce minimum/maximum relationships:

```dotenv
GRADSYNC_NOTIFICATION_REMINDER_LEAD_MINUTES=1440
GRADSYNC_NOTIFICATION_ESCALATION_DELAY_MINUTES=1440
GRADSYNC_NOTIFICATION_REPEAT_INTERVAL_MINUTES=1440
GRADSYNC_NOTIFICATION_MAX_REMINDERS=3
GRADSYNC_NOTIFICATION_THRESHOLD_MIN_MINUTES=60
GRADSYNC_NOTIFICATION_THRESHOLD_MAX_MINUTES=10080
GRADSYNC_REPORT_ANALYTICS_MAX_PERIODS=104
GRADSYNC_REPORT_ANALYTICS_CACHE_SECONDS=60
GRADSYNC_EXECUTION_JOB_BATCH_SIZE=200
```

Invalid production bounds must fail readiness before jobs start. No new secret,
host, queue, or external service setting is introduced.

## Acceptance Coverage Matrix

| Criterion | Primary automated evidence |
|---|---|
| AC-001 | Notification outcome/policy unit, integration, and contract suites |
| AC-002 | Mixed-recipient notification filter and project-isolation fixture |
| AC-003 | Domain-action reconciliation and five-second live-refresh e2e |
| AC-004 | Channel, quiet-hour, threshold, retry, and escalation policy matrix |
| AC-005 | Milestone derivation and task-does-not-accept unit suites |
| AC-006 | Deliverable lifecycle, immutable history, and concurrency integration |
| AC-007 | 200-item execution search/filter performance fixture |
| AC-008 | Reporting-period lock, historical render, and migration suites |
| AC-009 | Independent report aggregate fixture comparison |
| AC-010 | Analytics definition/source/export and no-ranking assertions |
| AC-011 | Decision supersession and risk lifecycle/history suites |
| AC-012 | Full role/direct-ID/stale-link authorization matrix |
| AC-013 | Audit event cardinality and safe-payload assertions |
| AC-014 | Playwright 390/900/1440 layout and overlap checks |
| AC-015 | English/Chinese key, fallback, notification, and export checks |
| AC-016 | Redis/email/analytics/calendar degradation and reconciliation |
| AC-017 | Moderated advisor journey fixture and acceptance record |
| AC-018 | Timed handover retrieval journey and acceptance record |

## Test-First Backend Validation

### 1. Notification outcome and policy rules

Write failing tests, then run:

```bash
cd backend
../.venv/bin/python -m pytest \
  tests/unit/test_notification_outcomes.py \
  tests/unit/test_notification_preferences.py \
  tests/unit/test_project_notification_policy.py \
  tests/integration/test_notification_follow_up.py \
  tests/contract/test_actionable_notifications_api.py
```

Expected:

- Delivery, read, acknowledgement, action completion, expiry, retry, and
  unavailable states remain independent.
- Repeated event/acknowledgement/reconciliation calls are idempotent.
- Reading never completes an action; only authoritative domain events do.
- quiet hours affect eligible non-urgent email only;
- primary-advisor project overrides remain inside bounds;
- 100 mixed notification fixtures return exact unread/pending filters with no
  cross-account/project record.

Evidence: AC-001..AC-004, AC-012, AC-013, AC-016.

### 2. Milestone and deliverable lifecycle

```bash
cd backend
../.venv/bin/python -m pytest \
  tests/unit/test_milestone_derivation.py \
  tests/unit/test_deliverable_rules.py \
  tests/unit/test_deliverable_review_authority.py \
  tests/contract/test_project_execution_api.py \
  tests/integration/test_deliverable_lifecycle.py \
  tests/integration/test_project_execution_concurrency.py
```

Expected:

- Required accepted deliverables are the only path to completed milestones.
- Task completion and progress percentage never imply acceptance.
- reviewer recommendations remain advisory; primary/co-advisor decision is
  final and attributable.
- submit/return/resubmit/accept/archive and stale version conflicts preserve
  immutable revisions/evidence;
- removed members and removed evidence leave safe historical state;
- 200-item filtered reads satisfy the 3-second p95 target.

Evidence: AC-005..AC-007, AC-011..AC-013.

### 3. Report template, periods, responses, and analysis

```bash
cd backend
../.venv/bin/python -m pytest \
  tests/unit/test_report_template_fields.py \
  tests/unit/test_reporting_period_lock.py \
  tests/unit/test_report_analytics.py \
  tests/contract/test_structured_reports_api.py \
  tests/integration/test_structured_report_revisions.py \
  tests/integration/test_report_template_migration.py \
  tests/integration/test_report_analytics_performance.py
```

Expected:

- only the seven controlled field types validate;
- both locale labels and field-specific constraints are required at publish;
- a period locks one version at opening for all students/revisions;
- historical legacy reports render through the default backfilled template;
- late/missing/review/execution/risk/metric aggregates exactly match independent
  fixtures and identify population, unit, range, missing values, and sources;
- no response or export includes ranks or opaque composite scores;
- 500 revisions and 104 periods satisfy bounded performance.

Evidence: AC-008..AC-010, AC-012, AC-013, AC-015, AC-016.

### 4. Decision and risk governance

```bash
cd backend
../.venv/bin/python -m pytest \
  tests/unit/test_decision_rules.py \
  tests/unit/test_risk_matrix.py \
  tests/unit/test_risk_transitions.py \
  tests/contract/test_project_governance_records_api.py \
  tests/integration/test_decision_risk_history.py \
  tests/integration/test_risk_escalation.py
```

Expected:

- published decisions are immutable and can only be superseded by a linked
  successor;
- all nine low/medium/high matrix combinations return the documented severity;
- only project members raise risks and only primary/co-advisors triage/close;
- blocker promotion deduplicates one open source risk;
- accepted/resolved risks stop reminders, reopening restarts review;
- every revision preserves actor, reason, state, matrix inputs, owner, and
  linked source.

Evidence: AC-011..AC-013.

### 5. Calendar, events, operations, and migration

```bash
cd backend
../.venv/bin/python -m pytest \
  tests/integration/test_execution_calendar_projections.py \
  tests/integration/test_project_execution_events.py \
  tests/integration/test_execution_operations.py \
  tests/integration/test_execution_migrations.py \
  tests/integration/test_production_readiness.py
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py migrate --plan
../.venv/bin/python manage.py check --deploy
../.venv/bin/ruff check .
```

Expected:

- milestone, deliverable, risk review, and reporting deadline projections
  appear once and update from source dates;
- repeated scheduler runs create no duplicate periods, reminders, escalations,
  attempts, or project events;
- readiness detects invalid bounds, missing Beat registration, migration
  incompleteness, worker/scheduler lag, and restore incompatibility;
- old tasks/reports/notifications/routes remain usable before and after
  application-only rollback.

Evidence: AC-003, AC-006, AC-008, AC-011, AC-013, AC-016.

## Contract and Schema Validation

```bash
bash scripts/check-openapi-contract.sh --strict-shapes \
  specs/017-research-execution-loop/contracts/openapi.yaml
cd backend
../.venv/bin/python -m pytest tests/contract/test_openapi_schema.py
```

Expected: every operation and required query/request/response status in
`contracts/openapi.yaml` is present in the generated schema, with no strict
shape drift.

## Test-First Frontend Validation

### Component and boundary tests

```bash
cd frontend
npm run test -- \
  tests/component/project-execution.test.tsx \
  tests/component/deliverable-review.test.tsx \
  tests/component/report-template-editor.test.tsx \
  tests/component/report-analytics.test.tsx \
  tests/component/actionable-notifications.test.tsx \
  tests/component/notification-preferences.test.tsx \
  tests/component/frontend-import-boundaries.test.ts
```

Expected:

- bounded list/detail selection retains stable layout and form state;
- role matrix omits forbidden controls;
- student, reviewer, advisor, observer, and administrator see the correct
  actions and protected context;
- template fields, risk matrix, report sources, notification outcomes, quiet
  hours, conflict states, and global toast behavior match the UI contract;
- no feature imports another feature's private `api.ts`.

Evidence: AC-001..AC-016.

### Browser, accessibility, and responsive journeys

```bash
cd frontend
GRADSYNC_E2E_MODE=fullstack \
GRADSYNC_BACKEND_PYTHON=../.venv/bin/python \
npm run test:e2e -- \
  research-execution.spec.ts \
  structured-reports.spec.ts \
  actionable-notifications.spec.ts \
  submission-review.spec.ts \
  dashboard-calendar.spec.ts \
  production-ui.spec.ts \
  accessibility.spec.ts
```

Expected:

- cross-session project events converge within five seconds without reload;
- the notification red dot clears on read while pending-action state remains;
- authoritative actions close linked notifications;
- the student submits a deliverable/report but cannot plan, accept, publish,
  triage, archive, or change project thresholds;
- the assigned reviewer recommends but cannot finally accept;
- advisors complete the full milestone, report, decision, and risk lifecycle;
- protected stale links disclose no title, member, count, or status;
- 390, 900, and 1440 CSS px have no overlap, clipped primary controls,
  unbounded panel growth, or page-level horizontal scroll;
- English/Chinese and keyboard/screen-reader paths are complete.

Evidence: AC-001..AC-018.

### Standard frontend gates

```bash
cd frontend
npm run lint
npm run test
npm run build
npm run check:pwa
```

Expected: ESLint, all Vitest tests, type checking, production build, and offline
shell validation pass. Cached protected data remains account-scoped; offline
creation/review is not implied.

## Manual Acceptance Journeys

### Advisor planning and student delivery

1. Sign in as the primary advisor, open `/projects/:projectId/execution`, and
   create two milestones with member owners.
2. Add required/optional deliverables, assign multiple students through the
   input-driven member combobox, link tasks, set acceptance criteria/dates, and
   confirm calendar projection.
3. Sign in as an assigned student. Confirm planning/archive/final-decision
   controls are absent. Update progress, add material/task/HTTPS evidence, and
   submit.
4. As assigned reviewer, recommend acceptance. Confirm the milestone remains
   incomplete.
5. As co-advisor, issue final acceptance. Confirm deliverable and milestone
   update within five seconds and all linked notifications complete correctly.

Expected: AC-003, AC-005..AC-007, AC-012, AC-017.

### Structured reporting

1. As advisor, create a draft template containing every controlled field type
   with bilingual labels and publish it.
2. Confirm the already-open period keeps its prior template; open the next
   period through the idempotent scheduler and confirm all students receive the
   new version.
3. Submit, return, and resubmit one student report. Verify each revision keeps
   the period-locked labels/values.
4. Open analytics for multiple periods, inspect metric definitions/source
   reports/missing counts, then export the same filters.

Expected: AC-008..AC-010, AC-015, AC-017..AC-018.

### Decisions and risks

1. Publish a decision linked to the accepted deliverable and report, then
   supersede it. Verify both records and the chain remain visible.
2. As student, raise a report blocker as a risk twice. Verify one source risk.
3. As advisor, triage all nine matrix combinations in fixtures, assign owner
   and treatment, then mitigate, accept/resolve, and reopen selected risks.
4. Advance review/due time and verify one active escalation with no duplicate
   reminder.

Expected: AC-004, AC-011..AC-013, AC-018.

### Notification preferences and administration

1. Configure quiet hours and disable report email. Verify in-app remains
   immediate, email is deferred/suppressed as allowed, and mandatory security
   email remains fixed.
2. Change project thresholds as primary advisor within bounds, then attempt an
   out-of-bounds value and the same action as co-advisor.
3. Read an acknowledgement-required item, verify it is still pending, then
   acknowledge it. Complete an action-required item through its target.
4. As administrator, inspect privacy-safe operational counts and audit evidence
   without notification subjects or report/rationale content.

Expected: AC-001..AC-004, AC-012..AC-016.

## Degradation and Recovery Validation

1. Stop Redis/worker after a successful load. Verify project source reads and
   in-app notifications remain available, analytics/calendar show bounded stale
   state, and last successful results/forms remain.
2. Restore worker/scheduler and run reconciliation repeatedly. Verify exactly
   one period, active reminder, escalation, delivery attempt key, and business
   completion per source event.
3. Fail email delivery until retry exhaustion. Verify in-app remains, delivery
   is not falsely `sent`, masked failure/lag metrics appear, and administrators
   can distinguish retry from terminal failure.
4. Remove membership while a protected detail/notification is open. Verify the
   next read/action clears project cache and reveals no hidden metadata.
5. Restore a backup in staging and compare counts/constraints for accepted
   deliverable revisions, report template locks/responses, decisions,
   risks/revisions, notification outcomes/attempts, and audit events.

Expected: AC-001, AC-003, AC-006, AC-008, AC-011..AC-016.

## Production Gate Order

1. Validate specification artifacts and current revision acceptance.
2. Run backend/frontend lint, unit, contract, integration, component, e2e,
   locale, accessibility, performance, and production readiness checks.
3. Validate strict OpenAPI drift and generated artifacts.
4. Back up PostgreSQL and verify restore compatibility.
5. Deploy additive schema, run bounded report backfill, and validate conflicts.
6. Deploy compatible application code with new jobs/routes disabled.
7. Run role/security smoke tests, then enable routes and existing Beat entries.
8. Observe scheduler lag, delivery/outcome counts, event convergence, aggregate
   failures, and error rates before completing release.

Application rollback disables feature routes/jobs but keeps additive data.
Rollback must not invent acknowledgement/acceptance, unlock a period template,
delete decision/risk history, or restore removed access.
