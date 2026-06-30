# Feature Specification: Research Group Operations

**Feature Branch**: `001-research-group-ops`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "Build an application that manages graduate research group operations, where advisors define projects with hierarchical tasks and deadlines, students submit version-tracked paper drafts and weekly progress reports with inline advisor commenting, and all research records (tasks, drafts, reports) are strictly grouped by project without cross-mixing across unrelated groups. The system must include lab equipment/seat booking and automatically send notification emails for pending reviews, approaching deadlines, and new submissions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Project Work (Priority: P1)

An advisor creates a research project, adds eligible students, defines task
hierarchies with deadlines, and tracks completion without exposing records from
unrelated projects or groups.

**Why this priority**: Project grouping and task ownership are the foundation for
all other research records. Drafts, reports, comments, bookings, and
notifications depend on project membership and project-scoped data boundaries.

**Independent Test**: Create two projects with different advisor/student
memberships, add parent and child tasks with deadlines to each, and verify each
participant only sees and updates records for projects where they are a member.

**Acceptance Scenarios**:

1. **Given** an advisor is creating a project, **When** they enter the project
   details and assign students, **Then** the project is available only to its
   assigned advisor and student members.
2. **Given** a project has a parent task, **When** the advisor adds child tasks
   with deadlines and assignees, **Then** the task hierarchy displays the
   parent-child relationship and each assignee sees their assigned work.
3. **Given** two unrelated projects exist, **When** a student opens task lists,
   draft history, reports, comments, or bookings, **Then** records from the
   unrelated project are not shown, linked, or searchable from that context.
4. **Given** a project deadline is approaching, **When** the notification window
   is reached, **Then** assigned participants receive an email reminder for the
   relevant project and task.

---

### User Story 2 - Review Drafts and Progress Reports (Priority: P2)

A student submits version-tracked paper drafts and weekly progress reports under
the correct project, and the advisor reviews them with inline comments that
remain attached to the submitted version.

**Why this priority**: Draft and progress review is a core research workflow and
depends on the project boundaries established in the first story.

**Independent Test**: Submit multiple draft versions and weekly reports for a
project, add advisor comments to specific passages or report sections, and
verify version history, comment placement, and review status remain intact.

**Acceptance Scenarios**:

1. **Given** a student belongs to a project, **When** they submit a new paper
   draft, **Then** the submission is saved as a new version with submitter,
   timestamp, title, and review status.
2. **Given** an advisor is reviewing a draft version, **When** they add inline
   comments to selected content, **Then** those comments remain attached to that
   draft version and are visible to permitted project members.
3. **Given** a student submits a weekly progress report, **When** the advisor
   reviews it, **Then** the advisor can add inline comments and mark the report
   as reviewed or needing revision.
4. **Given** a draft or report is submitted, **When** the submission is saved
   successfully and enters the review queue, **Then** the advisor receives an
   email notification for the new review item.
5. **Given** a submitted draft or report is awaiting review, **When** it remains
   pending beyond the configured review reminder period, **Then** the advisor
   receives a pending-review email reminder.

---

### User Story 3 - Reserve Lab Resources (Priority: P3)

Project members reserve lab equipment or seats for project work, avoid booking
conflicts, and view reservations only within projects where they are authorized.

**Why this priority**: Resource booking supports research operations but can be
delivered after core project and review workflows are available.

**Independent Test**: Create equipment and seat availability, reserve resources
for project members, attempt conflicting bookings, and verify project-scoped
visibility and email confirmations.

**Acceptance Scenarios**:

1. **Given** a project member needs a lab resource, **When** they select an
   available equipment item or seat and time window, **Then** the booking is
   confirmed for that project and visible to authorized project members.
2. **Given** a resource is already reserved for a time window, **When** another
   user attempts an overlapping booking, **Then** the system prevents the
   conflict and explains the unavailable time.
3. **Given** a booking is created, changed, or cancelled, **When** the action is
   completed, **Then** affected participants receive an email notification.

### Edge Cases

- A student belongs to multiple projects and must choose the target project
  before submitting drafts, reports, or bookings.
- An advisor attempts to move a task, draft, report, or comment from one project
  to an unrelated project.
- A child task deadline is set after its parent task deadline.
- A draft receives a new version after advisor comments were added to an older
  version.
- A weekly report is submitted late, skipped, duplicated for the same week, or
  edited after advisor review.
- A notification recipient is no longer a member of the project before the
  notification is sent.
- Two users attempt to reserve the same equipment or seat for overlapping times.
- A project is archived while tasks, pending reviews, bookings, or notification
  reminders are still open.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow advisors to create, update, archive, and
  view research projects with project name, description, advisor ownership,
  student membership, status, and relevant dates.
- **FR-002**: The system MUST restrict each project record to authorized members
  of that project and MUST prevent tasks, drafts, reports, comments, and bookings
  from appearing in unrelated project contexts.
- **FR-003**: The system MUST allow advisors to define hierarchical tasks within
  a project, including parent task, child tasks, assignees, status, priority, and
  deadlines.
- **FR-004**: The system MUST validate task hierarchy rules so child tasks remain
  within the same project as their parent and cannot create circular task
  relationships.
- **FR-005**: The system MUST allow advisors and assigned students to update task
  status according to their role, while preserving a visible history of status
  changes.
- **FR-006**: The system MUST allow students to submit paper drafts under a
  project and automatically preserve each submission as a distinct version with
  submitter, timestamp, title, file or content reference, and review status.
- **FR-007**: The system MUST allow advisors to add inline comments to specific
  locations in a draft version and keep those comments associated with the same
  version even after later versions are submitted.
- **FR-008**: The system MUST allow students to submit one weekly progress report
  per project week, including completed work, blockers, next steps, and optional
  attachments or links.
- **FR-009**: The system MUST allow advisors to add inline comments to progress
  reports and mark each report as reviewed, needing revision, or closed.
- **FR-010**: The system MUST provide project-scoped timelines or activity views
  that combine relevant tasks, draft submissions, report submissions, comments,
  bookings, and notification events for that project only.
- **FR-011**: The system MUST allow authorized users to view available lab
  equipment and seats, reserve them for project-related work, modify their own
  future reservations until the reservation start time, cancel their own future
  reservations until the reservation start time, and allow advisors to cancel
  project reservations when project policy or resource availability changes.
- **FR-012**: The system MUST prevent overlapping reservations for the same
  equipment item or seat and explain conflicts before a booking is confirmed.
- **FR-013**: The system MUST send notification emails for new draft submissions,
  new weekly report submissions, pending reviews, approaching task deadlines,
  approaching project deadlines, and booking changes.
- **FR-014**: Notification emails MUST identify the project, record type, due
  date or action needed, sender, and direct path back to the relevant project
  record.
- **FR-015**: The system MUST allow users to view notification delivery status
  for project records they are authorized to access.
- **FR-016**: The system MUST support advisor and student roles, with advisors
  able to manage project structure and reviews, and students able to manage their
  own submissions, assigned tasks, and bookings.
- **FR-017**: The system MUST preserve historical records for archived projects
  while preventing new tasks, submissions, comments, bookings, and deadline
  reminders unless the project is reopened.
- **FR-018**: The system MUST provide audit-visible timestamps and actor names
  for creation, submission, comment, review, booking, cancellation, archive, and
  status-change events.
- **FR-019**: The system MUST clearly indicate when a user is working inside a
  selected project and require project selection before creating tasks,
  submissions, reports, or bookings.
- **FR-020**: The system MUST provide user-friendly validation messages when an
  action fails because of project membership, record isolation, hierarchy,
  deadline, review, or booking conflict rules.

### User Experience Requirements *(include for user-facing work)*

- **UX-001**: The experience MUST keep project identity visible on every
  project-scoped screen so users can tell which project they are viewing or
  editing before taking action.
- **UX-002**: The experience MUST provide separate views for advisor project
  management, student assigned work, draft/report review queues, and resource
  booking while preserving a consistent navigation pattern.
- **UX-003**: The experience MUST provide clear loading, empty, success, warning,
  and error states for project creation, task updates, submissions, inline
  commenting, booking attempts, and notification delivery status.
- **UX-004**: The experience MUST support keyboard navigation and accessible
  labels for project selection, task hierarchy controls, draft/report comment
  actions, booking calendars, and notification settings.
- **UX-005**: The experience MUST warn users before actions that affect many
  records, including archiving a project, cancelling a booking, or closing a
  reviewed draft/report.

### Performance Requirements *(mandatory when user journeys can be measured)*

- **PERF-001**: Users MUST be able to open a project dashboard containing current
  tasks, latest draft status, latest report status, pending reviews, and upcoming
  bookings within 3 seconds for projects with up to 500 active records.
- **PERF-002**: Users MUST be able to filter or search project-scoped tasks,
  drafts, reports, comments, and bookings within 2 seconds for projects with up
  to 500 active records.
- **PERF-003**: Users MUST receive visible confirmation of submission, comment,
  task update, booking, or cancellation actions within 2 seconds under normal
  operating conditions.
- **PERF-004**: Deadline and review reminder emails MUST be queued or recorded
  within 5 minutes of becoming eligible for notification.
- **PERF-005**: The system MUST support at least 50 active projects and 500 total
  project members without degradation of the measurable user journeys above.

### Key Entities *(include if feature involves data)*

- **Research Project**: A project owned by an advisor and assigned to one or more
  students; defines the boundary for tasks, drafts, reports, comments, bookings,
  activity, and notifications.
- **Project Membership**: The association between a person, project, and role
  that determines what records they can see and what actions they can take.
- **Task**: A project-scoped work item with title, description, parent task,
  assignee, status, priority, deadline, and status history.
- **Paper Draft**: A project-scoped scholarly document submission with title,
  version number, submitter, submission time, content reference, review status,
  and version history.
- **Weekly Progress Report**: A project-scoped weekly update with reporting
  period, completed work, blockers, next steps, submitter, review status, and
  advisor comments.
- **Inline Comment**: Advisor feedback attached to a specific location in a
  draft version or progress report, with author, timestamp, status, and optional
  reply thread.
- **Lab Resource**: A bookable equipment item or seat with name, type,
  availability, location, and booking rules.
- **Booking**: A project-scoped reservation for a lab resource with requester,
  time window, status, and cancellation or change history.
- **Notification**: An email-triggering event tied to a project record, including
  recipient, reason, delivery status, and relevant action path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Advisors can create a project with members and a three-level task
  hierarchy in under 10 minutes during acceptance testing.
- **SC-002**: In cross-project access tests, 100% of tasks, drafts, reports,
  comments, and bookings remain visible only to authorized members of the
  relevant project.
- **SC-003**: Students can submit a new draft version and a weekly report for the
  correct project in under 5 minutes without advisor assistance.
- **SC-004**: Advisors can find pending draft and report reviews, add inline
  comments, and mark review status in under 5 minutes for a typical submission.
- **SC-005**: At least 95% of eligible notification events create a visible
  delivery record within 5 minutes of the triggering event or reminder window.
- **SC-006**: Resource booking conflict tests prevent 100% of overlapping
  reservations for the same seat or equipment item.
- **SC-007**: At least 90% of pilot users report that project context is clear
  before submitting records, commenting, or booking resources.
- **SC-008**: Project dashboard, project search/filter, and common record update
  actions meet the performance targets stated in this specification for the
  supported project size.

## Assumptions

- Advisors and students are authenticated users whose project access is based on
  explicit project membership.
- Advisors can manage projects they own; students can participate in multiple
  projects but cannot access unrelated project records.
- Draft submissions may represent uploaded files, rich text, or linked document
  content; the specification requires version tracking and comments regardless
  of storage format.
- Weekly reports follow a project-defined week and allow one active submission
  per student per project week unless reopened by an advisor.
- Pending-review reminders are sent to advisors when a draft or report remains
  unreviewed for 3 business days.
- Approaching-deadline reminders are sent 7 days and 1 day before task or
  project deadlines.
- Email is the required notification channel for this feature; in-app alerts may
  be added later but are not required for this specification.
- Archived projects remain readable to authorized members for historical
  continuity unless project policy later defines a retention period.

## Scope Decisions

- This feature covers project-scoped research operations: projects, tasks,
  draft/report submissions, inline review comments, resource bookings,
  notification delivery records, and the role-aware frontend workflows needed to
  complete those tasks.
- A full paper library/literature-management module, PDF reader annotations,
  DOI metadata ingestion, BibTeX/EndNote export, code repository browsing,
  repository diff/search workflows, and WebSocket real-time delivery are out of
  scope for this feature and should be specified as separate follow-up features.
- The frontend implementation remains aligned with the approved plan stack for
  this feature. Tailwind CSS, shadcn/ui, Redux Toolkit, and RTK Query are not
  adopted here because the planned and implemented frontend uses React 18,
  TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod, Vitest,
  and Playwright.
