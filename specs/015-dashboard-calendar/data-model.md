# Data Model: Dashboard Calendar and Scheduling

## Overview

The schedules domain persists authored schedule series, project/account
publication intent, temporal recipient grants, sparse occurrence changes,
reminders, revisions, and idempotent per-channel notification dispatches. The
submissions domain persists one optional weekly report schedule per project.
Project, task, report, and booking calendar items are derived at read time from
existing authoritative tables and are not copied into schedule storage.

All timed values are stored as timezone-aware UTC timestamps with an IANA
`timezone` name preserving the intended wall-clock context. All-day items use
local start/end dates with an exclusive end date. A schedule item uses exactly
one of the timed or all-day field pairs.

## Persisted Entities

### Schedule Item

Represents one private or published schedule series.

Fields:

- `id`: stable integer identifier.
- `owner`: required existing account that owns the record.
- `organizer`: required existing account shown for a published item; initially
  the owner.
- `scope`: `personal` or `group`.
- `category`: `personal`, `meeting`, `seminar`, `milestone`, `defense`,
  `deadline`, or `other`.
- `title`: required trimmed text, 1-255 characters.
- `description`: optional plain text, maximum 4,000 characters.
- `all_day`: boolean.
- `starts_at`, `ends_at`: nullable aware timestamps used only for timed items.
- `starts_on`, `ends_on`: nullable local dates used only for all-day items;
  `ends_on` is exclusive.
- `timezone`: required valid IANA timezone name, maximum 64 characters.
- `recurrence_frequency`: `none`, `daily`, `weekly`, or `monthly`.
- `recurrence_interval`: integer 1-30; `1` for non-recurring items.
- `recurrence_weekdays`: bounded list of ISO weekdays 1-7; non-empty only for
  weekly recurrence and without duplicates.
- `recurrence_until`: nullable local date; required for recurring items and no
  more than two years after the first local date.
- `status`: `active`, `completed`, or `cancelled`.
- `published_at`: nullable timestamp; required for visible group items.
- `cancelled_at`: nullable timestamp set when a group series is cancelled.
- `version`: positive integer starting at 1 and incremented on every accepted
  mutation.
- `created_at`, `updated_at`: lifecycle timestamps.

Relationships:

- Belongs to owner and organizer accounts.
- Has many Schedule Audiences, Schedule Recipient Grants, Occurrence Exceptions,
  Schedule Reminders, Schedule Revisions, and Notification Dispatches.

Validation and constraints:

- Personal items must have `owner == organizer`, have no audience/recipient
  rows, and are visible only to the owner.
- Group items can be created/published only by advisors or administrators.
- Timed items require `ends_at > starts_at` and no all-day date fields.
- All-day items require `ends_on > starts_on` and no timed fields.
- Recurring items require `recurrence_until`; non-recurring items do not accept
  recurrence weekdays or an end boundary.
- A series may generate at most 1,000 occurrences and span at most two years.
- `expectedVersion` must equal `version` for any mutation.
- Completed status applies to personal items or individual exceptions. Published
  group series are cancelled rather than deleted or globally completed.

Indexes:

- `(owner, scope, status, starts_at)` for private timed period reads.
- `(owner, scope, status, starts_on)` for private all-day reads.
- `(scope, status, published_at)` for staff group supervision.
- `(recurrence_frequency, recurrence_until)` for bounded recurrence candidates.
- `(updated_at, id)` for event-cursor derivation.

State transitions:

```text
personal active -> personal completed
personal completed -> personal active
personal active/completed -> deleted (confirmed)
personal active -> group active/published (explicit publish)
group active/published -> group cancelled
```

Transition rules:

- Publishing is atomic with audience validation/resolution and creates the first
  content-bearing group revision plus publication notifications.
- A personal-to-group publication stops being private only after the publication
  transaction succeeds; prior private audit content is not copied.
- Cancelled group series remain readable to historical/current authorized
  recipients according to the retention window but generate no new reminders.

### Schedule Audience

Stores the publisher's intended audience sources.

Fields:

- `id`: identifier.
- `schedule_item`: group item.
- `scope_type`: `project` or `account`.
- `project`: nullable project, required only for `project` scope.
- `account`: nullable account, required only for `account` scope.
- `created_by`: publisher/administrator that selected the scope.
- `created_at`: timestamp.

Validation and constraints:

- Exactly one source shape is valid: project only for `project` and account only
  for `account`.
- Project options must be active and visible to the publisher at publication.
- Advisor account options must be active members of projects the advisor can
  manage. Administrator account options may include any active account. The
  submitted account is revalidated at publication time.
- Students cannot create audience rows.
- Unique constraints prevent duplicate project or account source rows for one
  schedule item.
- Archived projects cannot be selected for new publication.
- At least one project or account audience is required; no all-account audience
  or endpoint exists.

Indexes:

- `(schedule_item, scope_type)`.
- `(project, schedule_item)` and `(account, schedule_item)`.

### Schedule Recipient Grant

Represents one immutable validity interval in the deduplicated
visibility/delivery history for a group item and account.

Fields:

- `id`: identifier.
- `schedule_item`: group item.
- `recipient`: existing account.
- `valid_from`: inclusive occurrence timestamp/date from which the grant applies.
- `valid_until`: nullable exclusive occurrence timestamp/date at which the grant
  stops; null means currently active.
- `source_types`: bounded list summarizing `project` and/or `account` resolution;
  no private profile data.
- `source_project_ids`: bounded IDs used for resolution evidence without copied
  project/member content.
- `resolved_at`: timestamp when this interval was opened or closed.

Validation and constraints:

- A conditional unique constraint permits at most one open grant for
  `(schedule_item, recipient)` while preserving closed historical grants.
- Recipient must be active when a grant is opened.
- Overlapping project/account scopes produce one open grant with merged sources.
- Selected-project scopes are re-resolved after membership changes and before
  future occurrences/reminders. A new member opens a grant from membership
  eligibility time; a departed member closes the grant without modifying it
  later.
- An explicitly selected account remains granted until removed from the audience
  or becomes inactive/ineligible; unrelated accounts never join automatically.
- A recipient may view a historical occurrence only when its occurrence key is
  inside one of that recipient's grant intervals.
- Closed grants cannot authorize future details or reminders and are never
  reopened; rejoining creates a new interval.

Indexes:

- `(recipient, schedule_item, valid_from, valid_until)` for period visibility.
- `(schedule_item, valid_until)` for current recipient resolution.
- `(resolved_at, valid_until)` for bounded re-resolution work.

State transitions:

```text
none -> open grant
open grant -> closed historical grant
closed historical grant + renewed eligibility -> new open grant
```

### Project Report Schedule

Represents one optional weekly progress-report deadline policy owned by an
active project in the submissions domain.

Fields:

- `id`: identifier.
- `project`: one-to-one active Research Project.
- `weekday`: ISO weekday 1-7.
- `deadline_time`: local time.
- `timezone`: valid IANA timezone name, maximum 64 characters.
- `version`: positive integer starting at 1 for stale-write protection.
- `updated_by`: authorized advisor/administrator.
- `created_at`, `updated_at`: lifecycle timestamps.

Validation and constraints:

- At most one policy per project.
- Only the project advisor/authorized teacher or administrator may create,
  update, or remove the policy.
- The project must be active when the policy is created or updated.
- No policy means no generated future report deadline; no workspace default is
  inferred.
- Archiving a project leaves the policy for rollback/history but suppresses new
  future deadline projections/reminders.
- Calendar projections use current active project membership and link to the
  project Reports view; they are read-only in calendar forms.

Indexes:

- Unique index on `project`.
- `(weekday, project)` for bounded due-window generation where needed.

State transitions:

```text
absent -> configured -> updated -> absent
configured + project archived -> retained/inactive projection
```

### Schedule Occurrence Exception

Stores a change to one generated occurrence or the split point for a future
series update.

Fields:

- `id`: identifier.
- `schedule_item`: parent series.
- `original_starts_at`: nullable original UTC timestamp for a timed occurrence.
- `original_starts_on`: nullable original local date for an all-day occurrence.
- `override_starts_at`, `override_ends_at`: nullable replacement timed range.
- `override_starts_on`, `override_ends_on`: nullable replacement all-day range.
- `override_title`, `override_description`: nullable occurrence-specific text.
- `status`: `rescheduled`, `completed`, or `cancelled`.
- `version`: positive integer for targeted stale-write protection.
- `created_by`, `created_at`, `updated_at`: actor and lifecycle timestamps.

Validation and constraints:

- Exactly one original occurrence key is present and matches the parent item's
  all-day mode.
- Unique original occurrence key per schedule item.
- Replacement ranges follow the same end-after-start rule as the parent.
- The original occurrence must belong to the bounded parent series.
- Group exceptions can be changed by the owning publisher or administrator;
  personal exceptions by the owner only.

Indexes:

- `(schedule_item, original_starts_at)`.
- `(schedule_item, original_starts_on)`.

### Schedule Reminder

Defines one reminder offset for a schedule item.

Fields:

- `id`: identifier.
- `schedule_item`: parent item.
- `offset_minutes`: one of `0`, `15`, `30`, `60`, `1440`, or `10080`.
- `mandatory`: boolean; only policy-created critical group reminders may be
  mandatory.
- `created_at`: timestamp.

Validation and constraints:

- Unique `(schedule_item, offset_minutes)`.
- Maximum three reminder rows per item.
- Reminder time is calculated from each effective occurrence start.
- Cancelled/completed/expired occurrences do not produce new reminders.

Index:

- `(offset_minutes, schedule_item)` supports reminder eligibility scans.

### Schedule Revision

Provides accountability for published group changes without exposing unrelated
private planning history.

Fields:

- `id`: identifier.
- `schedule_item`: group item.
- `revision_number`: positive sequential number.
- `actor`: account that accepted the change.
- `change_type`: `published`, `content_changed`, `time_changed`,
  `audience_changed`, `occurrence_changed`, or `cancelled`.
- `changed_fields`: bounded list of field names.
- `audience_summary`: counts by scope and resolved-recipient count.
- `effective_from`: nullable occurrence key for future-series changes.
- `created_at`: timestamp.

Validation and constraints:

- Unique `(schedule_item, revision_number)`.
- No private pre-publication title, description, recurrence, or reminder data is
  retained in revisions/audit.
- Revision writing is in the same transaction as the accepted group mutation.

Index:

- `(schedule_item, -revision_number)`.

### Schedule Notification Dispatch

Provides database-enforced idempotency between occurrence eligibility and the
existing Notification record.

Fields:

- `id`: identifier.
- `schedule_item`: group or personal item.
- `recipient`: account.
- `occurrence_key`: normalized UTC timestamp or all-day local-date key.
- `event_type`: `published`, `changed`, `cancelled`, `removed`, or `reminder`.
- `offset_minutes`: nullable; required only for reminders.
- `channel`: `in_app` or `email`.
- `notification`: nullable link to the existing Notification created after the
  dispatch claim.
- `status`: `claimed`, `created`, `skipped`, or `failed`.
- `failure_code`: privacy-safe code, not raw content.
- `created_at`, `updated_at`: lifecycle timestamps.

Validation and constraints:

- Unique `(schedule_item, recipient, occurrence_key, event_type,
  offset_minutes, channel)` with normalized null handling.
- Dispatch claims are created before Notification records in an atomic task
  transaction; retries reuse the same row.
- Recipient authorization/status is checked immediately before notification
  creation; no-longer-visible recipients become `skipped`.
- Publication and ordinary changes create only an `in_app` dispatch and a
  Notification marked with in-app-only delivery policy/status.
- Cancellation and reminder events create one `in_app` and one `email` dispatch;
  the single user-visible Notification references email delivery state without
  duplicating the top-notification entry.

Indexes:

- `(status, created_at)` for retry/operations.
- `(recipient, schedule_item, created_at)` for authorized delivery history.

### Notification Delivery Policy (additive existing entity fields)

Existing Notification records gain schedule-compatible delivery semantics.

Fields/choices:

- New event types: `schedule_published`, `schedule_changed`,
  `schedule_cancelled`, `schedule_recipient_removed`, and `schedule_reminder`.
- `delivery_policy`: `in_app` or `in_app_email`; existing rows default to
  `in_app_email` to preserve current behavior.
- Add status `in_app_only` as an explicit non-email terminal state so in-app-only
  records do not remain pending and are never selected by the email worker.

Rules:

- Every schedule event appears once in the existing in-app notification list.
- Only `schedule_cancelled` and `schedule_reminder` use `in_app_email`.
- Publication and ordinary-change event types use `in_app` and cannot be sent by
  email even after retry/requeue operations.
- Email retry/status remains on the existing notification record and dispatch;
  no new notification service or queue is introduced.

## Derived Entities

### Calendar Occurrence

The normalized API result produced from a Schedule Item/Exception or source
projection. It is not a table.

Fields:

- `occurrenceId`: stable compound identifier.
- `sourceType`: `schedule`, `project`, `task`, `report`, or `booking`.
- `sourceId`: source record identifier.
- `scheduleId`: nullable schedule identifier.
- `scope`: `personal`, `group`, or `system`.
- `category`, `title`, `description`, `allDay`, timed/date range, and timezone.
- `status`: effective active/completed/cancelled/source status.
- `organizer`: safe display identity when relevant.
- `audienceSummary`: group counts only; omitted for personal/system items.
- `actionPath`: authorized internal path.
- `capabilities`: `canView`, `canEdit`, `canDelete`, `canPublish`, `canCancel`,
  `canViewDeliveryStatus`, and `isReadOnly`.
- `version`: mutable schedule/exception version when applicable.

Generation rules:

- Schedule series expand only inside the requested period and merge exceptions.
- Private occurrences are included only for the owner.
- Group occurrences require a Schedule Recipient Grant valid for that
  occurrence key or authorized publisher/administrator supervision access.
- System projections repeat source-module visibility and status rules.
- Cancelled group occurrences remain visible for their relevant historical
  period; cancelled future occurrences generate no reminders.

### System Schedule Projection

Read-only mappings from existing records:

- Project start/end milestones: visible active or historical project members;
  action path `/projects/{id}`.
- Task deadlines: assigned students and project staff with existing task access;
  action path `/projects/{projectId}` selecting the task where supported.
- Configured future report deadlines: current active project members and
  authorized project staff, generated from Project Report Schedule; action path
  `/projects/{projectId}/reports`.
- Submitted report periods: report owner and authorized project reviewers;
  action path `/projects/{projectId}/reports`.
- Resource bookings: requester and authorized resource managers/reviewers;
  action path `/resources` with booking context where supported.

Projection rules:

- Source record dates/statuses are authoritative on every query.
- Missing, deleted, or unauthorized records emit no occurrence or action path.
- Projection mapping never grants broader access than the owning module.
- Source changes surface through calendar event invalidation, not copied rows.
- Unconfigured or archived projects emit no new future report-deadline
  occurrence or reminder.

### Schedule Event Cursor

A visibility-filtered incremental change shape derived from schedule updates,
recipient resolution, source-record updates, and relevant notification changes.
It is not required to be a separate table when existing update/audit markers can
provide an ordered cursor.

Fields:

- `eventId`: monotonic opaque cursor.
- `eventType`: safe invalidation category.
- `scheduleId` or source type/id when visible.
- `occurredAt`: timestamp.
- `latestEventId`, `generatedAt`: response freshness markers.

Privacy rule: private event cursors are emitted only to the owner and contain no
private title or description.

## Transaction Boundaries

- Create private: item + reminders.
- Publish/create group: item + project/account audiences + deduplicated open
  recipient grants + reminders + revision + in-app dispatch/notifications +
  audit.
- Update/cancel: row lock + expected-version check + item/exception mutation +
  audience resolution + revision + dispatch claims/notifications + audit.
- Recipient re-resolution: lock affected item/recipient set + close departed
  grants + open new-member grants + removal dispatches as required; closed
  history is not updated.
- Reminder batch: claim unique in-app/email dispatches + revalidate occurrence
  grant + create/update existing Notification + send email only when policy is
  `in_app_email`.
- Project report policy mutation: project authorization + expected-version check
  + policy write/removal + calendar invalidation/audit.

Side effects are transaction-aware; notification generation starts only after
the authoritative schedule transaction commits.

## Migration Approach

1. Add the new schedules app and tables with constraints/indexes.
2. Add the submissions-owned Project Report Schedule table; do not create a
   default/backfill for existing projects.
3. Add schedule notification event types, `delivery_policy`, and explicit
   in-app-only terminal status. Existing rows default to current email-capable
   behavior; generic target fields remain supported.
4. Register the schedule reminder generator in existing Beat setup after schema
   deployment.
5. Do not backfill schedule rows from projects, tasks, reports, or bookings;
   those remain runtime projections.
6. Validate forward migration on empty and production-shaped databases and run
   `makemigrations --check --dry-run` after committed migrations.

## Rollback Approach

- Disable schedule routes/UI and the schedule reminder periodic task first.
- Retain schedule tables and historical notification/audit rows during normal
  application rollback so old code ignores them safely.
- Reverse migrations only after a verified backup and explicit approval to
  discard schedule history; reversal is not part of routine rollback.
- Existing projects, tasks, reports, bookings, resources, notifications, and
  audit records are never rewritten or deleted by feature rollback.
