# Data Model: Research Group Operations

## Entity Overview

```text
User
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
│       ├── Notification
│       └── AuditEvent
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
  and audit events
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
