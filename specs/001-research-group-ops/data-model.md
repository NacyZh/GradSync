# Data Model: Research Group Operations

## Entity Overview

```text
User
├── UserLocalePreference
├── ProjectMembership
│   └── ResearchProject
│       ├── Task
│       ├── Draft
│       │   └── DraftVersion
│       │       └── InlineComment
│       ├── WeeklyProgressReport
│       │   └── InlineComment
│       ├── Booking
│       │   └── LabResource
│       ├── PaperRecord
│       │   └── PaperAttachment
│       ├── PaperImportBatch
│       ├── CodeArtifact
│       │   └── CodeArtifactVersion
│       ├── DownloadEvent
│       ├── Notification
│       └── AuditEvent

FrontendViewModel
├── WorkspaceShellState
├── ProjectContextState
├── ReviewWorkspaceState
├── BookingWorkspaceState
├── LibraryWorkspaceState
├── CodeRepositoryWorkspaceState
├── LocaleState
└── NotificationCenterState
```

## User

Represents an authenticated person who can participate in research projects.

**Fields**
- `id`: stable unique identifier
- `name`: display name
- `email`: unique email address used for notifications
- `global_role`: account-level role, such as advisor, student, or administrator
- `status`: active, suspended, archived
- `created_at`, `updated_at`

**Relationships**
- Has many `ProjectMembership` records
- Authors tasks, submissions, comments, bookings, notifications, and audit events
- Has one `UserLocalePreference`

**Validation Rules**
- Email must be unique and deliverable format
- Suspended or archived users cannot create new project records

## ResearchProject

Defines the strict boundary for research records and membership.

**Fields**
- `id`
- `title`
- `description`
- `advisor_id`
- `status`: active, archived
- `starts_on`
- `ends_on`
- `created_at`, `updated_at`, `archived_at`

**Relationships**
- Has many memberships, tasks, drafts, weekly reports, bookings, notifications,
  paper records, paper import batches, code artifacts, download events, and audit
  events
- Belongs to one advisor owner

**Validation Rules**
- Advisor owner must have advisor privileges
- Active projects can create records; archived projects are read-only unless
  reopened
- Project date range must be valid when both dates are present

**State Transitions**
- active -> archived
- archived -> active

## ProjectMembership

Connects users to projects and controls project-scoped access.

**Fields**
- `id`
- `project_id`
- `user_id`
- `role`: advisor, student, reviewer, observer
- `status`: active, removed
- `joined_at`, `removed_at`

**Relationships**
- Belongs to one `ResearchProject`
- Belongs to one `User`

**Validation Rules**
- A user can have only one active membership per project
- Removed members cannot access new project activity unless explicitly restored
- Advisors can manage project structure; students can manage assigned work,
  submissions, and their own eligible bookings

## Task

A hierarchical project-scoped work item.

**Fields**
- `id`
- `project_id`
- `parent_task_id`
- `title`
- `description`
- `assignee_id`
- `status`: not_started, in_progress, blocked, submitted, completed, cancelled
- `priority`: low, normal, high, urgent
- `deadline_at`
- `created_by_id`
- `created_at`, `updated_at`, `completed_at`

**Relationships**
- Belongs to one project
- May have one parent task in the same project
- May have many child tasks
- May be assigned to a project member
- Has many audit events and notifications

**Validation Rules**
- Parent task must belong to the same project
- Parent-child cycles are forbidden
- Child task deadline cannot be later than parent deadline unless explicitly
  accepted by an advisor during planning
- Assignee must be an active member of the same project

**State Transitions**
- not_started -> in_progress, cancelled
- in_progress -> blocked, submitted, completed, cancelled
- blocked -> in_progress, cancelled
- submitted -> in_progress, completed, cancelled
- completed and cancelled are terminal unless reopened by an advisor

## Draft

Groups versions of a paper draft within a project.

**Fields**
- `id`
- `project_id`
- `title`
- `student_id`
- `status`: active, closed
- `created_at`, `updated_at`

**Relationships**
- Belongs to one project
- Has many draft versions
- Belongs to a project student

**Validation Rules**
- Student must be an active project member
- Closed drafts cannot receive new versions unless reopened by an advisor

## DraftVersion

An immutable submission of draft content.

**Fields**
- `id`
- `draft_id`
- `project_id`
- `version_number`
- `submitted_by_id`
- `content_reference`
- `summary`
- `review_status`: pending_review, reviewed, needs_revision, closed
- `submitted_at`
- `reviewed_at`

**Relationships**
- Belongs to one draft and one project
- Has many inline comments
- Has notifications and audit events

**Validation Rules**
- Version numbers increment within a draft
- Submitted-by user must be an active member of the same project
- Comments must remain attached to this exact version

**State Transitions**
- pending_review -> reviewed, needs_revision, closed
- needs_revision -> reviewed, closed
- reviewed -> closed

## WeeklyProgressReport

A student's weekly update for one project.

**Fields**
- `id`
- `project_id`
- `student_id`
- `report_week_start`
- `completed_work`
- `blockers`
- `next_steps`
- `attachment_reference`
- `review_status`: pending_review, reviewed, needs_revision, closed
- `submitted_at`
- `reviewed_at`

**Relationships**
- Belongs to one project
- Belongs to one student member
- Has many inline comments
- Has notifications and audit events

**Validation Rules**
- One active report per student, project, and reporting week
- Student must be an active member of the project
- Reviewed reports require advisor action before student edits are accepted

**State Transitions**
- pending_review -> reviewed, needs_revision, closed
- needs_revision -> pending_review, reviewed, closed
- reviewed -> closed

## InlineComment

Advisor feedback anchored to a draft version or progress report.

**Fields**
- `id`
- `project_id`
- `target_type`: draft_version, progress_report
- `target_id`
- `author_id`
- `anchor`
- `body`
- `status`: open, resolved
- `created_at`, `updated_at`, `resolved_at`

**Relationships**
- Belongs to one project
- Belongs to one target record in the same project
- Belongs to an advisor or reviewer member

**Validation Rules**
- Target record must belong to the same project
- Author must have review privileges in the target project
- Anchor must identify a location in the submitted version or report

**State Transitions**
- open -> resolved
- resolved -> open

## LabResource

An equipment item or seat that can be reserved.

**Fields**
- `id`
- `name`
- `resource_type`: equipment, seat
- `location`
- `status`: available, unavailable, retired
- `booking_policy`
- `created_at`, `updated_at`

**Relationships**
- Has many bookings

**Validation Rules**
- Retired resources cannot receive new bookings
- Booking policy defines maximum duration and eligible users if restricted

## Booking

A project-scoped reservation for a lab resource.

**Fields**
- `id`
- `project_id`
- `resource_id`
- `requested_by_id`
- `starts_at`
- `ends_at`
- `status`: reserved, cancelled, completed
- `purpose`
- `created_at`, `updated_at`, `cancelled_at`

**Relationships**
- Belongs to one project
- Belongs to one lab resource
- Belongs to one requester who must be a project member
- Has notifications and audit events

**Validation Rules**
- End time must be after start time
- Requester must be an active project member
- Active reservations for the same resource cannot overlap
- Archived projects cannot create or change active bookings

**State Transitions**
- reserved -> cancelled, completed
- cancelled and completed are terminal

## Notification

A record of an email-triggering event.

**Fields**
- `id`
- `project_id`
- `recipient_id`
- `event_type`: new_submission, pending_review, approaching_deadline,
  booking_changed
- `target_type`
- `target_id`
- `subject`
- `status`: pending, queued, sent, failed, skipped
- `eligible_at`
- `queued_at`
- `sent_at`
- `failure_reason`
- `created_at`

**Relationships**
- Belongs to one project
- Belongs to one recipient
- Targets a project-scoped record

**Validation Rules**
- Recipient must be authorized for the project at send time
- Target record must belong to the same project
- Failed notifications can be retried while the target remains actionable

**State Transitions**
- pending -> queued, skipped
- queued -> sent, failed
- failed -> queued, skipped

## PaperRecord

A project-scoped literature item used as a searchable/downloadable research
asset.

**Fields**
- `id`
- `project_id`
- `title`
- `authors`: ordered author display strings or normalized author records
- `venue`
- `publication_year`
- `doi`
- `external_ids`: source-specific identifiers such as arXiv, PubMed, Semantic
  Scholar, or imported catalog IDs
- `abstract`
- `notes`
- `tags`
- `import_source`: manual, doi, bibtex, file_metadata, batch
- `fingerprint`: normalized deduplication fingerprint
- `created_by_id`
- `created_at`, `updated_at`, `archived_at`
- `status`: active, duplicate_blocked, archived

**Relationships**
- Belongs to one project
- Has zero or more `PaperAttachment` records
- May be created by a `PaperImportBatch`
- Has download events, audit events, and optional notifications

**Validation Rules**
- Project must be active for new imports or metadata edits
- DOI and external identifiers must be normalized before matching
- Active paper records in the same project cannot share the same file checksum,
  DOI/external identifier, or normalized title-first-author-year fingerprint
- Tags must be project-scoped and user-visible before filtering
- Download requires current project membership

**State Transitions**
- active -> archived
- duplicate_blocked is an import result state and cannot be downloaded

## PaperAttachment

File metadata for a paper record.

**Fields**
- `id`
- `paper_id`
- `project_id`
- `storage_key`
- `filename`
- `content_type`
- `size_bytes`
- `checksum_sha256`
- `uploaded_by_id`
- `created_at`
- `status`: active, replaced, archived

**Relationships**
- Belongs to one `PaperRecord` and one project
- Has download events and audit events

**Validation Rules**
- Attachment project must match paper project
- Checksum must be calculated before commit
- File type and size must satisfy project policy

**State Transitions**
- active -> replaced, archived

## PaperImportBatch

Staging and result record for a paper import operation.

**Fields**
- `id`
- `project_id`
- `requested_by_id`
- `source_type`: file, doi, bibtex, mixed
- `status`: staged, committed, failed, cancelled
- `total_items`
- `accepted_count`
- `duplicate_count`
- `error_count`
- `result_summary`
- `created_at`, `committed_at`

**Relationships**
- Belongs to one project
- May create many `PaperRecord` and `PaperAttachment` records
- Has audit events

**Validation Rules**
- Batch items must be validated and duplicate-checked before commit
- Duplicate results must include the matched paper ID and match reason
- Archived projects cannot commit new imports

**State Transitions**
- staged -> committed, failed, cancelled

## CodeArtifact

A project-scoped code package, source archive, or repository snapshot.

**Fields**
- `id`
- `project_id`
- `name`
- `description`
- `tags`
- `status`: active, superseded, archived
- `created_by_id`
- `created_at`, `updated_at`, `archived_at`

**Relationships**
- Belongs to one project
- Has many `CodeArtifactVersion` records
- Has download events and audit events

**Validation Rules**
- Name must be unique among active code artifacts in the same project
- Archived projects cannot create or upload code versions
- Search and download visibility is limited to current project members

**State Transitions**
- active -> superseded, archived
- superseded -> active, archived

## CodeArtifactVersion

Immutable uploaded version of a code artifact.

**Fields**
- `id`
- `artifact_id`
- `project_id`
- `version_label`
- `commit_reference`
- `release_notes`
- `storage_key`
- `filename`
- `content_type`
- `size_bytes`
- `checksum_sha256`
- `uploaded_by_id`
- `uploaded_at`
- `status`: active, superseded, archived

**Relationships**
- Belongs to one `CodeArtifact` and one project
- Has download events and audit events

**Validation Rules**
- Version label or commit reference must be present
- Version label and checksum cannot duplicate an active version in the same
  artifact unless explicitly superseding
- File type and size must satisfy project policy
- Download requires current project membership

**State Transitions**
- active -> superseded, archived

## DownloadEvent

Audit-visible event for paper and code downloads.

**Fields**
- `id`
- `project_id`
- `actor_id`
- `target_type`: paper_attachment, code_artifact_version
- `target_id`
- `filename`
- `checksum_sha256`
- `downloaded_at`
- `delivery_mode`: direct_response, signed_url

**Relationships**
- Belongs to one project and actor
- Targets one downloadable paper or code file
- Mirrors an `AuditEvent`

**Validation Rules**
- Actor must be an active project member at download time
- Target must belong to the same project and be downloadable

## UserLocalePreference

Persisted interface language preference.

**Fields**
- `user_id`
- `locale`: en, zh
- `updated_at`

**Relationships**
- Belongs to one user
- Read by `WorkspaceShellState` and `LocaleState`

**Validation Rules**
- Unsupported locales fall back to English
- Locale changes must not modify stored research content or authorization

## AuditEvent

Immutable record of significant project activity.

**Fields**
- `id`
- `project_id`
- `actor_id`
- `event_type`
- `target_type`
- `target_id`
- `summary`
- `created_at`

**Relationships**
- Belongs to one project
- May belong to one actor
- Targets one project-scoped record

**Validation Rules**
- Target record must belong to the same project when a target is present
- Audit events are append-only

## FrontendViewModel

Client-side view state that composes server-owned project records into
production-grade role workflows. These are not persisted database entities; they
define the frontend architecture contract for Tailwind CSS and shadcn/ui
implementation.

**Fields**
- `active_role`: advisor, student, reviewer, administrator
- `active_project_id`
- `navigation_items`: role-filtered links with label, icon, route, and disabled
  reason when unavailable
- `pending_actions`: actionable user tasks derived from tasks, submissions,
  bookings, comments, and notifications
- `feedback_state`: loading, empty, success, warning, error, confirming
- `theme`: light, dark, system

**Relationships**
- Reads `User`, `ProjectMembership`, `ResearchProject`, `Task`,
  `DraftVersion`, `WeeklyProgressReport`, `Booking`, `PaperRecord`,
  `CodeArtifact`, `Notification`, `UserLocalePreference`, and `AuditEvent` API
  responses through typed TanStack Query hooks
- Renders accessible shadcn/ui primitives through GradSync shared UI adapters

**Validation Rules**
- Must never infer authorization from client state; server responses remain the
  source of truth
- Must keep project identity visible before project-scoped create, submit,
  comment, review, book, cancel, archive, or reopen actions
- Must expose recoverable feedback for validation, permission, network, and
  background-delivery failures
- Must preserve keyboard navigation, focus management, labels, and contrast for
  every workflow route

## WorkspaceShellState

Role-aware application shell used on authenticated routes.

**Fields**
- `current_user`
- `sidebar_collapsed`
- `selected_project_summary`
- `global_search_query`
- `notification_summary`
- `theme_preference`
- `locale_preference`

**Relationships**
- Uses `User`, visible projects, notification summary endpoints, and locale
  preference endpoints
- Owns top-level navigation, project switcher, notification entry point, theme
  control, and language switcher

**Validation Rules**
- Advisor-only and administrator-only destinations must be hidden or disabled
  for users without that role
- Collapsed, tablet, and mobile navigation states must retain accessible labels
  and focus order

## ProjectContextState

View state for project-scoped dashboards and workflows.

**Fields**
- `project`
- `task_filters`
- `submission_filters`
- `booking_filters`
- `paper_filters`
- `code_filters`
- `activity_filters`
- `selected_record_id`
- `dirty_form_state`

**Relationships**
- Reads project dashboard, task, submission, booking, paper, code,
  notification, and audit responses for one project

**Validation Rules**
- Changing projects must clear record selection and unsaved form state after
  confirmation
- Empty states must explain whether no records exist or the current filters hide
  all records

## ReviewWorkspaceState

View state for draft and weekly report review.

**Fields**
- `selected_review_target_type`
- `selected_review_target_id`
- `comment_anchor`
- `comment_draft`
- `review_status_pending`
- `version_compare_mode`

**Relationships**
- Composes `Draft`, `DraftVersion`, `WeeklyProgressReport`, and `InlineComment`
  records

**Validation Rules**
- Comments must show the selected version/report context before submission
- Review status controls must be disabled with clear reasons when the project is
  archived or the user lacks review privileges

## BookingWorkspaceState

View state for resource availability and booking management.

**Fields**
- `availability_window`
- `resource_filters`
- `selected_resource_id`
- `booking_form_state`
- `conflict_explanation`
- `cancel_confirmation_state`

**Relationships**
- Composes `LabResource`, `Booking`, project membership, and notification
  records

**Validation Rules**
- Start and end time controls must prevent invalid ranges before submit
- Started bookings must render as immutable with a clear explanation
- Destructive cancellation must use a confirmation dialog with focus trapping

## LibraryWorkspaceState

View state for project paper library import, search, detail, and download.

**Fields**
- `paper_search_query`
- `paper_filters`: author, venue, year, tag, DOI, import source, uploader
- `selected_paper_id`
- `import_batch_state`
- `duplicate_review_state`
- `upload_progress`
- `download_status`

**Relationships**
- Composes `PaperRecord`, `PaperAttachment`, `PaperImportBatch`, and
  `DownloadEvent` records for one project

**Validation Rules**
- Selected project context must be visible before import, edit, or download
- Duplicate matches must show match reason and existing paper reference
- Download controls must be disabled with explanation when unauthorized

## CodeRepositoryWorkspaceState

View state for project code artifact upload, search, version detail, and
download.

**Fields**
- `code_search_query`
- `code_filters`: tag, status, uploader, version label, commit reference
- `selected_artifact_id`
- `selected_version_id`
- `upload_progress`
- `supersede_confirmation_state`
- `download_status`

**Relationships**
- Composes `CodeArtifact`, `CodeArtifactVersion`, and `DownloadEvent` records
  for one project

**Validation Rules**
- Project context must be visible before upload, archive, supersede, or download
- Upload form must validate archive type, size, and version/reference metadata
- Download controls must be disabled with explanation when unauthorized

## LocaleState

Client-side view state for Chinese/English language switching.

**Fields**
- `active_locale`: en, zh
- `available_locales`
- `message_catalog_version`
- `fallback_locale`
- `is_persisting`

**Relationships**
- Reads and updates `UserLocalePreference`
- Provides localized labels and messages to workspace shell and workflow views

**Validation Rules**
- Locale switch must preserve current route, project context, and focus order
- Missing localized strings must fall back deterministically to English
- Validation and error states must remain semantically equivalent across locales
