# Data Model: Research Execution Loop

## Conventions

- All project-owned rows contain a direct `project` foreign key even when the
  project is reachable through another relation. Services validate equality;
  the direct key keeps authorization and indexes explicit.
- Mutable planning records use a positive `version` beginning at 1.
  `expectedVersion` is required for updates that can race.
- Actor relationships use `PROTECT` unless account deletion policy requires a
  safe snapshot. Project-child records follow the existing confirmed project
  deletion policy; governance audit snapshots remain outside the project
  cascade.
- User-entered text is plain text. Titles are trimmed, non-empty, and at most
  255 characters. Explanations/rationales are at most 8,000 characters unless a
  narrower field rule is listed.
- Potentially large collections are page/cursor bounded. All timestamps are
  timezone-aware; project execution dates are project-local dates where no time
  is required.
- State changes are performed through domain services, never by direct generic
  model updates.

## Projects Domain

### Milestone

Represents an ordered project outcome boundary.

Fields:

- `id`: identifier.
- `project`: owning Research Project.
- `title`: required, maximum 255.
- `description`: plain text, maximum 8,000.
- `target_date`: required project-local date.
- `order`: non-negative integer unique within active/archived project records.
- `current_status`: `planned`, `in_progress`, `at_risk`, `blocked`, `overdue`,
  `completed`, or `archived`; service-derived.
- `completed_at`: nullable timestamp set only when every required deliverable
  has an accepted advisor decision.
- `archived_at`: nullable timestamp.
- `version`: optimistic concurrency value.
- `created_by`, `created_at`, `updated_at`: attribution.

Relationships:

- Has many Milestone Owners, Deliverables, Project Record Links, and audit
  events.
- Appears in the calendar through a read-only date projection.

Constraints and validation:

- Project must be active and writable for create/update/archive.
- At least one active project member is an owner.
- `completed_at` is present only for `completed`.
- `archived_at` is present only for `archived`.
- Users cannot write `current_status` directly.
- Reordering is atomic and preserves one stable order value per project.

Indexes:

- Unique `(project, order)`.
- `(project, current_status, target_date, order)`.
- `(project, archived_at, order)`.

Derived-state precedence:

```text
archived
  > completed (all required deliverables accepted)
  > blocked (any required deliverable blocked)
  > overdue (target date passed and not completed)
  > at_risk (linked open high risk or incomplete work inside reminder window)
  > in_progress (any required deliverable started/submitted/returned)
  > planned
```

### Milestone Owner

Fields:

- `milestone`, `user`: relationship.
- `assigned_by`, `assigned_at`: attribution.

Constraints:

- Unique `(milestone, user)`.
- User must have active membership in the same project when assigned.
- Membership removal leaves the historical row but marks the milestone as
  requiring owner correction; it never silently selects a replacement.

Index: `(user, milestone)`.

### Deliverable

Represents one expected output inside a milestone.

Fields:

- `id`, `project`, `milestone`.
- `title`, `description`.
- `acceptance_criteria`: required plain text, maximum 8,000.
- `due_date`: required project-local date.
- `required`: boolean, default true.
- `reviewer_required`: boolean; when true at least one active reviewer
  designation is required before submission.
- `order`: non-negative integer unique inside a milestone.
- `current_status`: `planned`, `in_progress`, `blocked`, `submitted`,
  `under_review`, `changes_requested`, `accepted`, or `archived`.
- `progress_percent`: integer 0-100; informative and never sufficient for
  acceptance.
- `blocker_summary`: required when status becomes `blocked`, otherwise blank.
- `current_revision`: nullable current submitted Deliverable Revision.
- `accepted_revision`: nullable accepted Deliverable Revision.
- `accepted_at`: nullable timestamp.
- `archived_at`: nullable timestamp.
- `version`, `created_by`, `created_at`, `updated_at`.

Constraints and validation:

- Milestone and deliverable project IDs must match.
- At least one active project member is assigned before submission.
- Reviewer-required deliverables need at least one active Deliverable Reviewer
  Designation before submission.
- Submission requires non-empty acceptance criteria and at least one evidence
  item.
- `accepted_revision` must belong to this deliverable and have an accepted
  advisor final decision.
- Accepted records cannot return to ordinary editing. A changed output creates
  a new revision only after an authorized return/reopen flow.
- Required deliverables cannot be archived while their milestone remains
  completed; milestone status is reconciled in the same transaction.

Indexes:

- Unique `(milestone, order)`.
- `(project, current_status, due_date)`.
- `(milestone, required, current_status)`.
- `(project, archived_at, updated_at)`.

State transitions:

```text
planned -> in_progress | blocked | archived
in_progress -> blocked | submitted | archived
blocked -> in_progress | submitted | archived
submitted -> under_review | changes_requested | accepted
under_review -> changes_requested | accepted
changes_requested -> in_progress | submitted
accepted -> archived
archived -> archived
```

Only an advisor final decision enters `accepted` or `changes_requested`.
Reviewer recommendations do not directly transition the deliverable.

### Deliverable Assignee

Fields:

- `deliverable`, `user`.
- `assigned_by`, `assigned_at`, `removed_at`.

Constraints:

- Unique open assignment per `(deliverable, user)`.
- User must be an active member of the same project when assigned.
- Removed/deactivated membership closes the assignment and surfaces an
  unassigned warning; historical submission attribution remains.

Indexes:

- `(user, removed_at, deliverable)`.
- `(deliverable, removed_at)`.

### Deliverable Reviewer Designation

Stores reviewers selected during deliverable planning. A designation does not
itself grant access to an unsubmitted revision.

Fields:

- `deliverable`, `reviewer`.
- `designated_by`, `designated_at`, `removed_at`.

Constraints:

- Unique open designation per `(deliverable, reviewer)`.
- Reviewer must be an active approved teacher with primary advisor,
  co-advisor, or reviewer membership in the same project.
- On submission, current designations become target-specific Submission Review
  Assignments for that immutable revision.
- Removing a designation affects future submissions and does not revoke or
  rewrite a completed historical recommendation.

Indexes:

- `(deliverable, removed_at)`.
- `(reviewer, removed_at, deliverable)`.

### Deliverable Task Link

Fields:

- `deliverable`, `task`.
- `linked_by`, `linked_at`.

Constraints:

- Unique `(deliverable, task)`.
- Task and deliverable must belong to the same project.
- Task deletion removes the live link but accepted revision evidence retains a
  minimized source snapshot.

Indexes: `(task, deliverable)` and `(deliverable, task)`.

### Deliverable Revision

Immutable submission of one deliverable.

Fields:

- `id`, `project`, `deliverable`.
- `revision_number`: positive integer.
- `criteria_snapshot`: acceptance criteria at submission.
- `description_snapshot`: submitted output description.
- `submitted_by`, `submitted_at`.
- `idempotency_key`: client retry key.
- `state`: `submitted`, `recommended_accept`, `recommended_return`,
  `accepted`, or `returned`.

Constraints:

- Unique `(deliverable, revision_number)`.
- Conditional unique `(deliverable, idempotency_key)` when non-empty.
- Submitter is an active assignee or an advisor acting with a recorded reason.
- Immutable after creation except service-owned state projection.

Indexes:

- `(deliverable, -revision_number)`.
- `(project, state, submitted_at)`.

### Deliverable Evidence

Immutable evidence attached to a Deliverable Revision.

Fields:

- `id`, `project`, `revision`.
- Exactly one live source: `project_material`, `task`,
  `weekly_progress_report`, or `external_url`.
- `label_snapshot`, `source_type_snapshot`, `source_id_snapshot`.
- `added_by`, `created_at`.

Constraints:

- Exactly one source shape at creation.
- Internal source belongs to the same project and is visible to the actor.
- External URL uses `https`, maximum 2,048 characters, and is rendered with
  safe browser isolation.
- If a live source is removed, its nullable FK clears while minimized snapshot
  fields remain; no content body, private path, or account identity is copied.

Indexes:

- `(revision, id)`.
- `(project_material, revision)`, `(task, revision)`, and
  `(weekly_progress_report, revision)` where non-null.

### Deliverable Review Recommendation

Fields:

- `id`, `project`, `revision`, `reviewer`.
- `recommendation`: `accept` or `return`.
- `rationale`: required.
- `review_assignment`: target-specific Submission Review Assignment.
- `created_at`, `superseded_at`.

Constraints:

- Reviewer must hold an active assignment to this revision/target and eligible
  reviewer project membership.
- At most one non-superseded recommendation per `(revision, reviewer)`.
- Recommendation is advisory and cannot set final deliverable status.
- A changed recommendation supersedes the old row instead of overwriting it.

Indexes:

- `(revision, superseded_at, created_at)`.
- `(reviewer, superseded_at, created_at)`.

### Deliverable Final Decision

Fields:

- `id`, `project`, `revision`.
- `decision`: `accepted` or `returned`.
- `rationale`: required for return; optional for acceptance.
- `decided_by`: active primary advisor or co-advisor.
- `decided_at`.
- `idempotency_key`.

Constraints:

- One final decision per revision.
- Conditional unique `(project, idempotency_key)` when non-empty.
- Reviewer recommendation, when required, must exist before final decision.
- The decision and deliverable/milestone derivation occur in one transaction.
- Rows are immutable.

Indexes:

- `(project, decision, decided_at)`.
- `(revision, decided_at)`.

### Decision Record

Immutable published project decision.

Fields:

- `id`, `project`, `title`.
- `context`: required.
- `options_considered`: bounded ordered string list, 1-20 entries, each at most
  1,000 characters.
- `outcome`: required.
- `rationale`: required.
- `owner`: active primary/co-advisor responsible for follow-through.
- `effective_date`: required.
- `status`: `current` or `superseded`.
- `supersedes`: nullable prior Decision Record in the same project.
- `published_by`, `published_at`.
- `idempotency_key`: client retry key.

Constraints:

- Published records are immutable.
- A superseding decision is created atomically and marks exactly its direct
  predecessor `superseded`.
- A decision cannot supersede itself, cross projects, or create a cycle.
- A predecessor can have at most one current direct successor.
- Conditional unique `(project, idempotency_key)` when non-empty.

Indexes:

- `(project, status, effective_date)`.
- `(project, owner, status)`.
- Unique conditional `supersedes` when non-null.

State transitions:

```text
new -> current
current + successor publication -> superseded
superseded -> superseded
```

### Risk Record

Current project risk state.

Fields:

- `id`, `project`, `title`, `description`.
- `source_type`: `manual`, `report_blocker`, `deliverable`, or `decision`.
- `source_key`: stable dedupe key for promoted source.
- `likelihood`: `low`, `medium`, or `high`.
- `impact`: `low`, `medium`, or `high`.
- `severity`: `low`, `medium`, or `high`; service-derived.
- `owner`: nullable active project member until triaged.
- `treatment`: required after triage.
- `review_date`: nullable until triaged, then required.
- `state`: `raised`, `open`, `mitigating`, `accepted`, or `resolved`.
- `closure_rationale`: required for accepted/resolved.
- `closed_at`: nullable.
- `version`, `raised_by`, `created_at`, `updated_at`.
- `idempotency_key`: client retry key for initial creation.

Fixed severity matrix:

| Likelihood \ Impact | Low | Medium | High |
|---|---|---|---|
| Low | Low | Low | Medium |
| Medium | Low | Medium | High |
| High | Medium | High | High |

Constraints:

- `severity` cannot be supplied by clients.
- Unique `(project, source_type, source_key)` when `source_key` is non-empty
  prevents repeated blocker promotion.
- Conditional unique `(project, idempotency_key)` when non-empty.
- Owner must be an active project member when assigned.
- Triaged open/mitigating risks require owner, treatment, and review date.
- Accepted/resolved risks require closure rationale and `closed_at`; they emit
  no further reminder until reopened.
- Reopen clears closure fields, enters `open`, and requires an active owner and
  future review date.

Indexes:

- `(project, state, severity, review_date)`.
- `(owner, state, review_date)`.
- `(project, source_type, source_key)`.
- `(project, updated_at, id)`.

State transitions:

```text
raised -> open | mitigating | accepted | resolved
open -> mitigating | accepted | resolved
mitigating -> open | accepted | resolved
accepted -> open
resolved -> open
```

Only primary/co-advisors triage or close. Any active project member may raise a
risk. Student updates after raising are limited to additional source context
until triage.

### Risk Revision

Immutable history row created on each accepted risk mutation.

Fields:

- `id`, `project`, `risk`, `revision_number`.
- `previous_state`, `new_state`.
- Snapshots of likelihood, impact, severity, owner ID, treatment, review date,
  and closure rationale.
- `actor`, `reason`, `created_at`.
- `idempotency_key`: transition retry key.

Constraints:

- Unique `(risk, revision_number)`.
- Conditional unique `(risk, idempotency_key)` when non-empty.
- Created in the same transaction as the Risk Record update.
- No update/delete through normal application controls.

Index: `(risk, -revision_number)`.

### Project Record Link

Bounded relationship from a Decision Record or Risk Record to affected work.

Fields:

- `id`, `project`.
- Exactly one source: `decision` or `risk`.
- Exactly one target: `milestone`, `deliverable`, `task`, `project_material`,
  `weekly_progress_report`, `decision_target`, or `risk_target`.
- `target_type_snapshot`, `target_id_snapshot`, `label_snapshot`.
- `created_by`, `created_at`.

Constraints:

- Exactly one source and one target.
- Source and live target belong to the same project.
- Duplicate source/target pairs are rejected.
- Removing a target clears only the live FK and preserves minimized snapshot
  fields; authorization is rechecked before showing a live link.

Indexes:

- Per-source indexes `(decision, id)` and `(risk, id)`.
- Per-target indexes for each nullable target FK.

## Submissions Domain

### Report Template

Logical template identity owned by one project.

Fields:

- `id`, `project`, `name`.
- `active_version`: nullable published Report Template Version.
- `created_by`, `created_at`, `updated_at`.

Constraints:

- One logical default template per project in this feature.
- Project deletion follows existing cascade; archive makes template read-only.

Index: unique `(project)`.

### Report Template Version

Fields:

- `id`, `project`, `template`, `version_number`.
- `status`: `draft`, `published`, or `superseded`.
- `version`: optimistic edit value for draft updates.
- `created_by`, `created_at`, `published_by`, `published_at`.

Constraints:

- Unique `(template, version_number)`.
- At most one draft and one published active version per template.
- Only draft versions are editable.
- Publishing requires at least one field and all field definitions valid.
- Publication atomically supersedes the previous active version and updates
  `ReportTemplate.active_version`.
- Published/superseded versions and fields are immutable.

Indexes:

- `(project, status, version_number)`.
- `(template, status)`.

State transitions:

```text
draft -> published
published + later publication -> superseded
superseded -> superseded
```

### Report Template Field

Fields:

- `id`, `template_version`, `key`: stable machine key.
- `label_en`, `label_zh`: required bilingual labels.
- `help_text_en`, `help_text_zh`.
- `field_type`: `long_text`, `number`, `percentage`, `single_choice`,
  `multiple_choice`, `execution_progress`, or `risk_blocker`.
- `required`: boolean.
- `order`: non-negative integer.
- `unit`: nullable, maximum 40; only number fields.
- `options`: bounded list of `{value,labelEn,labelZh}` for choice fields.
- `min_value`, `max_value`: nullable decimals for number/percentage.
- `analytics_enabled`: allowed for number, percentage, execution progress, and
  risk/blocker counts.

Constraints:

- Unique `(template_version, key)` and `(template_version, order)`.
- Percentage range is always 0-100.
- Choice fields require 1-50 unique options; other fields reject options.
- Long text rejects numeric constraints; number min must not exceed max.
- Labels are complete in both locales before publication.
- At most 50 fields per template version.

Indexes:

- `(template_version, order)`.
- `(template_version, analytics_enabled, field_type)`.

### Reporting Period

Fields:

- `id`, `project`.
- `starts_on`, `ends_on`: inclusive/exclusive weekly period boundaries.
- `deadline_at`: timezone-aware deadline from Project Report Schedule.
- `template_version`: immutable version locked at opening.
- `state`: `open` or `closed`.
- `opened_at`, `closed_at`.
- `generation_key`: stable scheduler idempotency key.

Constraints:

- Unique `(project, starts_on)`.
- Unique `generation_key`.
- `ends_on = starts_on + 7 days`.
- Template version belongs to the same project and was published by opening.
- Template version never changes after creation.
- Archived projects do not open new periods.

Indexes:

- `(project, starts_on, state)`.
- `(state, deadline_at)`.
- `(template_version, starts_on)`.

### Weekly Progress Report Extensions

Existing `WeeklyProgressReport` retains `completed_work`, `blockers`,
`next_steps`, `attachment_reference`, `report_week_start`, and current review
fields during compatibility.

Add fields:

- `reporting_period`: nullable during migration, required for new submissions.
- `template_version`: locked period version.
- `submitted_late`: boolean derived against period deadline.
- `idempotency_key`: retry key.
- `response_schema_version`: positive integer.

Constraints:

- Existing unique `(project, student, report_week_start, revision_number)`
  remains.
- Reporting period, template version, report project, and week must agree.
- Every new revision in one project/student/period uses the same template.
- Conditional unique `(project, student, idempotency_key)` when non-empty.
- Existing return/resubmit review lifecycle remains authoritative.

Indexes:

- `(reporting_period, student, -revision_number)`.
- `(project, submitted_late, review_status, submitted_at)`.

### Report Response

One immutable field value for one submitted report revision.

Fields:

- `id`, `project`, `report`, `template_field`.
- `value`: bounded validated JSON scalar/list/reference payload.
- `numeric_value`: nullable decimal for number/percentage or computed count.
- `source_type`, `source_id`: nullable permitted execution source.
- `created_at`.

Constraints:

- Unique `(report, template_field)`.
- Field belongs to the report's locked template version.
- Required fields must have a non-empty valid response before submission.
- `numeric_value` is set only by server validation and preserves the declared
  unit/range.
- Execution progress references milestones/deliverables in the same project.
- Risk/blocker values may create or link a Risk Record only through the
  explicit promotion service.
- Rows are immutable with their report revision.

Indexes:

- `(project, template_field, numeric_value)`.
- `(report, template_field)`.
- `(source_type, source_id)`.

### Analytics Result

No durable analytics table is introduced. A response object contains:

- project, requested range, population count, generated time, source event
  version;
- submission counts: expected, on-time, late, missing, accepted, returned;
- milestone/deliverable state counts;
- blocker/risk counts by state/severity;
- metric series for analytics-enabled template fields, with unit, period,
  sample count, missing count, and source report IDs.

Rules:

- Range is at most 104 periods.
- Missing responses are null and excluded from numeric denominators; missing
  reports are counted only by the missing-submission metric.
- No ranking, composite productivity score, or unsupported inference.
- Redis cache TTL is at most 60 seconds and invalidates by project event
  version/template publication/report review changes.

## Notifications Domain

### Notification Extensions

Existing recipient-specific Notification retains its delivery summary fields.

Add fields:

- `category`: `security`, `project`, `deliverable`, `report`, `decision`,
  `risk`, `schedule`, or `administration`.
- `requirement_type`: `informational`, `acknowledgement`, or `action`.
- `outcome_state`: `not_required`, `pending`, `acknowledged`, `completed`,
  `expired`, or `unavailable`.
- `due_at`, `expires_at`: nullable.
- `acknowledged_at`, `action_completed_at`, `expired_at`, `unavailable_at`.
- `completion_event_type`, `completion_event_id`: safe authoritative source.
- `dedupe_key`: stable category/target/recipient/window key.
- `active_follow_up`: boolean.
- `reminder_count`, `escalation_level`.
- `last_reminded_at`, `last_escalated_at`.

Constraints:

- Informational notifications use `not_required` and no action timestamps.
- Acknowledgement-required transitions from pending to acknowledged.
- Action-required transitions from pending to completed only through a
  registered authoritative domain resolver.
- Expired/unavailable are terminal and set `active_follow_up=false`.
- Conditional unique `(recipient, dedupe_key)` while `active_follow_up=true`.
- Reading does not alter outcome fields.

Indexes:

- `(recipient, outcome_state, created_at)`.
- `(recipient, category, created_at)`.
- `(active_follow_up, due_at, outcome_state)`.
- `(project, outcome_state, due_at)`.
- `(status, eligible_at)` remains for delivery.

Outcome transitions:

```text
informational: not_required
acknowledgement: pending -> acknowledged | expired | unavailable
action: pending -> completed | expired | unavailable
```

### Notification Delivery Attempt

Fields:

- `id`, `notification`.
- `channel`: `in_app` or `email`.
- `attempt_number`.
- `state`: `pending`, `queued`, `sent`, `failed`, or `skipped`.
- `eligible_at`, `attempted_at`, `completed_at`.
- `failure_code`, `failure_reason_masked`.
- `idempotency_key`.

Constraints:

- Unique `(notification, channel, attempt_number)`.
- Unique `idempotency_key`.
- Failure reason is masked/truncated and cannot contain message body, address
  secrets, tokens, or credentials.
- Existing Notification delivery status remains a backward-compatible summary
  derived from attempts.

Indexes:

- `(state, eligible_at, channel)`.
- `(notification, channel, -attempt_number)`.

### Notification Preference Profile

Fields:

- `user`: one-to-one account.
- `quiet_hours_enabled`, `quiet_starts_at`, `quiet_ends_at`.
- `timezone`: valid IANA timezone.
- `version`, `updated_at`.

Constraints:

- Start/end required together when enabled and must define a non-zero window.
- Quiet hours delay eligible non-urgent email; they do not change in-app
  availability, due date, read/outcome state, or mandatory security delivery.

### Notification Category Preference

Fields:

- `profile`, `category`.
- `email_enabled`: boolean.
- `updated_at`.

Constraints:

- Unique `(profile, category)`.
- In-app is always enabled and therefore not user-configurable.
- Security email remains enabled for mandatory security event types regardless
  of stored preference.

### Project Notification Policy

Fields:

- `project`: one-to-one.
- `reminder_lead_minutes`.
- `escalation_delay_minutes`.
- `repeat_interval_minutes`.
- `max_reminders`: positive integer.
- `version`, `updated_by`, `created_at`, `updated_at`.

Constraints:

- Only the active primary advisor updates this policy.
- Values must stay inside environment-defined minimum/maximum bounds.
- No policy row means documented system defaults.
- Updating policy affects future eligible follow-up and never changes source
  due dates or completes current outcomes.

Index: `(updated_at, project)`.

## Existing Domain Integration

### Tasks

- No task field is removed.
- Deliverable Task Link owns the many-to-many relationship.
- Task status informs context but never final deliverable acceptance.
- Task deletion is allowed under existing permission; accepted evidence keeps a
  minimized snapshot only.

### Submission Review Assignment

- Extend the existing exactly-one-target constraint with nullable
  `deliverable_revision`.
- Submitting a reviewer-required deliverable creates one active assignment per
  current Deliverable Reviewer Designation.
- Assignment removal immediately blocks future reads/recommendations, while a
  previously submitted recommendation remains in immutable history.
- Existing weekly report, writing version, and legacy draft targets remain
  backward compatible.

### Schedules

- No new mutable Schedule Item is created.
- `projection_services` adds source types `milestone`, `deliverable`,
  `risk_review`, and `reporting_period`.
- Projection identifier is stable from source type/source ID/date/version.
- Source action path points to an authorized project execution/report detail.
- Calendar event cursor advances after source audit events.

### Audit

Existing Audit Event receives new event types and safe target snapshots:

- milestone/deliverable create/update/archive/submit/recommend/decide;
- report template draft/publish, period open, report submit/review/export;
- decision publish/supersede;
- risk raise/triage/transition/escalate;
- notification preference/project policy/acknowledge/complete/escalate;
- administrator supervision/export actions.

Audit persistence is required in the same transaction for privileged decisions,
acceptance, closure, policy changes, and administrative intervention.

## Migration Plan

### Migration A: Add empty schema

1. Create project execution/governance tables and indexes.
2. Create report template/field/period/response tables and nullable extension
   fields on Weekly Progress Report.
3. Add Notification extension fields with backward-compatible defaults:
   `category=project`, `requirement_type=informational`,
   `outcome_state=not_required`, and `active_follow_up=false`.
4. Create delivery attempt, preference, and project policy tables.
5. Do not register new periodic jobs yet.

### Migration B: Bounded report backfill

For projects in primary-key chunks:

1. Create the logical default template and published version with bilingual
   `completed_work`, `blockers`, and `next_steps` fields.
2. Create one Reporting Period per distinct historical `report_week_start`.
3. Attach each Weekly Progress Report to its period/template and create
   immutable Report Responses from legacy columns.
4. Record migration counters and conflicts without changing report review
   status or submission time.
5. Make new submissions require period/template after the backfill reaches that
   project; keep database columns nullable until a later cleanup feature if
   zero-downtime rollout requires it.

### Deployment activation

1. Deploy code that reads both legacy and new report shapes.
2. Validate old and new contracts, project isolation, and aggregate fixtures.
3. Register the existing Beat schedule entries idempotently.
4. Enable frontend routes after API readiness and migration completion.

## Rollback and Restore

- Application rollback disables new routes, projections, and scheduled tasks
  while leaving additive schema and rows intact.
- Old report clients continue to use retained legacy columns and URLs.
- Existing notification list/read behavior continues from old fields; new
  outcome history remains dormant and is not rewritten.
- Never reverse backfilled report values by deleting templates/periods or
  truncate deliverable/decision/risk history.
- Backup/restore verification must prove row counts and referential integrity
  for accepted deliverable revisions, report template locks/responses,
  notification outcomes/attempts, decisions/supersession, risks/revisions, and
  audit events before feature activation.
