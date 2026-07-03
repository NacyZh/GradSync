# Feature Specification: Research Group Operations

**Feature Branch**: `001-research-group-ops`

**Created**: 2026-06-25

**Status**: Draft - project owner confirmed; testing and development review pending

**Input**: User description: "Build an application that manages graduate research group operations, where advisors define projects with hierarchical tasks and deadlines, students submit version-tracked paper drafts and weekly progress reports with inline advisor commenting, and all research records (tasks, drafts, reports) are strictly grouped by project without cross-mixing across unrelated groups. The system must include lab equipment/seat booking and automatically send notification emails for pending reviews, approaching deadlines, and new submissions."

## Clarifications

### Session 2026-07-02

- Q: Which stakeholder review status should this spec record before implementation continues? → A: Project owner confirmed only; testing and development formal review remain pending.
- Q: What matching precedence should paper import use when multiple duplicate signals are present? → A: File checksum > DOI/external ID > normalized title, first author, and year.
- Q: What uniqueness policy should code artifacts use for version labels or commit references? → A: A project cannot reuse the same version label or commit/reference across active, archived, or superseded code artifacts.
- Q: What persistence scope should the Chinese/English language preference use? → A: The preference is bound to the user account and applies across devices after sign-in.
- Q: What import size and format policy should paper and code assets use? → A: Paper attachments are limited to 50 MB and PDF, BibTeX, or text metadata files; code artifacts are limited to 200 MB and zip or tar.gz archives.
- Q: How should the paper and code libraries be populated? → A: They are team public libraries populated from user-selected local folders or local files; no default automatic external search or online discovery runs.
- Q: How should professional resources be represented? → A: Resource types, fields, policies, and availability metadata are configurable because different disciplines use different resource catalogs.
- Q: How should language switching behave? → A: Chinese/English switching updates the visible interface immediately without a full reload while persisting the account preference.
- Q: What production readiness corrections are required? → A: Remove prototype descriptions and placeholder behavior, provide a centered login screen with a real background, and support email delivery plus delivery-status records.

## Constitution II Specification Modules

### Business Background, User Roles, and Core Goals

GradSync supports graduate research groups that need one project-centered
workspace for research planning, student submissions, advisor review,
customizable resource coordination, shared team research asset libraries,
notification visibility, and language preference. The primary users are
advisors, students, reviewers, and administrators. Advisors own project
structure, membership, reviews, and policy decisions. Students manage assigned
work, submissions, reports, bookings, and authorized research assets. Reviewers
can participate in permitted review workflows. Administrators manage
account-level operations, professional resource templates, and email delivery
configuration without bypassing project authorization.

The core goals are to keep all research records isolated by project membership,
make advisor/student workflows independently testable, preserve versioned review
history, prevent booking conflicts, keep paper and code downloads authorized at
request time, and allow Chinese or English interface use without changing stored
research content.

### Complete Positive Business Flows

The positive flows are represented by User Story 1 through User Story 4. An
advisor creates a project, assigns students, and builds a task hierarchy. A
student submits draft versions and weekly reports for a selected project. An
advisor reviews those submissions with anchored inline comments and status
changes. Project members reserve available resources from a configurable
discipline-specific resource catalog without conflicts. Authorized project
members import papers and code artifacts from user-selected local folders into
team public libraries, add descriptions and metadata, search project assets on
explicit user action, download authorized files to their local device, and
switch the workspace language between Chinese and English while preserving
project context.

### Exception, Boundary, and Degradation Scenarios

The exception and boundary scenarios are represented by the Edge Cases section
and the import, download, archived-project, membership, duplicate-detection,
booking-conflict, notification, and locale requirements. The system must reject
cross-project access, invalid task hierarchies, duplicate weekly reports,
comment targets outside the same project, overlapping bookings, unsupported or
oversized local imports, duplicate paper imports, duplicate code versions or
commit references, unauthorized downloads, unsupported custom resource fields,
automatic external library searches, and new records in archived projects.
Notification delivery delays or failures must still leave visible delivery
status for authorized users.

### Quantifiable and Automatable Acceptance Criteria

The Independent Test, Acceptance Scenarios, Functional Requirements, Performance
Requirements, and Success Criteria sections define automatable acceptance
criteria. Each user story includes a standalone test path. Cross-project
isolation, duplicate prevention, booking conflict prevention, download
authorization, import rejection, locale persistence, and notification timing are
measured through explicit pass/fail outcomes rather than subjective inspection.

### Dependencies, Assumptions, and Unsupported Capabilities

Dependencies and business assumptions are recorded in the Assumptions and Scope
Decisions sections. The current scope depends on authenticated users, explicit
project membership, email as the required notification channel, managed file
attachments or object-storage references, local browser file/folder selection,
and application-owned Chinese/English interface strings. Unsupported
capabilities include PDF reader annotations, citation formatting engines,
EndNote export, automatic full-text translation, automatic online paper/code
search, hosted Git replacement, server-side repository diff browsing, merge
requests, CI execution for imported code, and WebSocket real-time collaboration.

## Stakeholder Review Status

Project owner review is confirmed as of 2026-07-02. Formal testing stakeholder
review and formal development stakeholder review remain pending. Implementation
may proceed only with this risk explicitly tracked in `plan.md`; release remains
blocked until testing and development review are completed or an approved,
time-bounded exception is recorded.

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

### User Story 3 - Configure and Reserve Research Resources (Priority: P3)

Administrators and advisors configure discipline-specific resource types and
fields, project members reserve eligible resources for project work, avoid
booking conflicts, and view reservations only within projects where they are
authorized.

**Why this priority**: Resource booking supports research operations but can be
delivered after core project and review workflows are available.

**Independent Test**: Create custom resource types for two different
professional contexts, add resource items with type-specific fields, reserve
resources for project members, attempt conflicting bookings, and verify
project-scoped visibility and email confirmations.

**Acceptance Scenarios**:

1. **Given** an administrator or advisor defines a resource type, **When** they
   add custom fields, eligibility rules, and availability policy, **Then** the
   resource catalog stores the type without requiring code changes for that
   discipline.
2. **Given** a project member needs a configured resource, **When** they select
   an available resource item and time window, **Then** the booking is confirmed
   for that project and visible to authorized project members.
3. **Given** a resource is already reserved for a time window, **When** another
   user attempts an overlapping booking, **Then** the system prevents the
   conflict and explains the unavailable time.
4. **Given** a booking is created, changed, or cancelled, **When** the action is
   completed, **Then** affected participants receive an email notification.

---

### User Story 4 - Manage Research Assets and Language Preference (Priority: P2)

Project members maintain project-scoped team public libraries that include paper
records and code artifacts imported from local folders, can add descriptions,
prevent duplicates, search locally indexed assets only on explicit user action,
download authorized assets to their local device, and can switch the web
interface between Chinese and English in real time.

**Why this priority**: Papers and code are core research outputs that belong
with the same project boundary as tasks, submissions, reports, and reviews.
Language switching is required so Chinese and English users can complete the
same operational workflows without separate deployments.

**Independent Test**: Import duplicate and non-duplicate papers from a local
folder into one project, import code files from local folders into two different
projects with descriptions, search and download authorized records, verify no
automatic external search occurs, verify unrelated project assets are not
visible, and switch the interface between Chinese and English while preserving
the active route and project context.

**Acceptance Scenarios**:

1. **Given** a project member imports papers from a selected local folder
   containing paper files and metadata files, **When** one imported item matches
   an existing paper fingerprint, DOI, title and year, or normalized external
   identifier in that project, **Then** the system prevents a duplicate and
   explains which existing paper matched.
2. **Given** a project contains paper records, **When** an authorized member
   searches by title, author, venue, year, tag, DOI, or imported metadata,
   **Then** matching papers are returned only from the team library for projects
   where the member has access and downloadable files are offered only when the
   user is authorized.
3. **Given** a project member imports code files for a project from a selected
   local folder or local archive, **When** they provide a description,
   version/reference metadata, tags, and optional release notes, **Then** the
   code artifact is stored in that project's team public code library and can be
   searched, versioned, downloaded, or superseded without appearing in other
   project libraries.
4. **Given** a user changes the interface language, **When** they choose Chinese
   or English from the workspace shell, **Then** navigation, forms, validation
   feedback, empty states, confirmations, and workflow labels change language
   immediately without losing the current route, selected project, or unsaved
   form warning.
5. **Given** an unauthenticated user opens the login screen, **When** the page
   renders on desktop or mobile, **Then** the login form is centered over a real
   background visual and exposes production sign-in errors without sample account
   copy.

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
- Two users attempt to reserve the same custom resource item for overlapping
  times.
- A project is archived while tasks, pending reviews, bookings, or notification
  reminders are still open.
- Two imported papers have the same DOI but different uploaded files, or no DOI
  but matching normalized title, first author, and year.
- A paper local-folder import includes malformed BibTeX, missing metadata, a
  duplicate file checksum, a hidden/system file, or a file type that is not
  allowed by project policy.
- A code local-folder import is too large, has an unsupported archive or file
  type, duplicates an existing checksum/version label, or belongs to an archived
  project.
- A user switches language while a form has unsaved changes or while validation
  errors are visible.
- An administrator adds a custom resource field with an unsupported type,
  removes a field already used by active bookings, or changes a booking policy
  that affects existing reservations.
- Email delivery credentials are missing, the SMTP provider fails, or a
  recipient is no longer eligible at send time.

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
- **FR-011**: The system MUST allow administrators and authorized advisors to
  define custom resource types, fields, eligibility rules, locations,
  availability policies, and resource items so different specialties can manage
  different resource catalogs without code changes.
- **FR-012**: The system MUST allow authorized users to view available custom
  resources, reserve them for project-related work, modify their own future
  reservations until the reservation start time, cancel their own future
  reservations until the reservation start time, and allow advisors to cancel
  project reservations when project policy or resource availability changes.
- **FR-013**: The system MUST prevent overlapping reservations for the same
  resource item and explain conflicts before a booking is confirmed.
- **FR-014**: The system MUST send notification emails for new draft submissions,
  new weekly report submissions, pending reviews, approaching task deadlines,
  approaching project deadlines, and booking changes.
- **FR-015**: Notification emails MUST identify the project, record type, due
  date or action needed, sender, and direct path back to the relevant project
  record.
- **FR-016**: The system MUST allow users to view notification delivery status
  for project records they are authorized to access.
- **FR-017**: The system MUST support advisor and student roles, with advisors
  able to manage project structure and reviews, and students able to manage their
  own submissions, assigned tasks, and bookings.
- **FR-018**: The system MUST preserve historical records for archived projects
  while preventing new tasks, submissions, comments, bookings, and deadline
  reminders unless the project is reopened.
- **FR-019**: The system MUST provide audit-visible timestamps and actor names
  for creation, submission, comment, review, booking, cancellation, archive, and
  status-change events.
- **FR-020**: The system MUST clearly indicate when a user is working inside a
  selected project and require project selection before creating tasks,
  submissions, reports, or bookings.
- **FR-021**: The system MUST provide user-friendly validation messages when an
  action fails because of project membership, record isolation, hierarchy,
  deadline, review, or booking conflict rules.
- **FR-022**: The system MUST provide a project-scoped paper team library where
  authorized members can create, import from selected local folders or local
  files, update metadata, search, view, and download paper records and attached
  files for projects they can access.
- **FR-023**: Paper import MUST support local folder/file import of PDF,
  BibTeX, and text metadata files, MUST NOT perform default automatic external
  search or DOI lookup, and MUST prevent duplicates within a project using file
  checksum, supplied DOI/external identifier, and normalized title,
  first-author, and year matching. When multiple duplicate signals are present,
  the duplicate explanation MUST use the strongest matching rule in this order:
  file checksum, DOI/external identifier, then normalized title, first author,
  and year.
- **FR-024**: The system MUST allow project members to tag, describe, and filter
  papers by title, authors, venue, year, DOI, tags, import source, local folder
  path label, and uploader while preserving project isolation.
- **FR-025**: The system MUST provide a project-scoped code team library where
  authorized members can import code files from selected local folders or local
  archives, add descriptions, add version/reference metadata, search records,
  download authorized artifacts to local storage, and supersede or archive old
  versions.
- **FR-026**: Code artifacts MUST be isolated by project and MUST preserve
  uploader, checksum, version label or commit reference, import timestamp,
  source folder path label, file metadata, description, download audit trail,
  and archive/supersede status. Within the same project, a version label or
  commit/reference MUST remain unique across active, archived, and superseded
  code artifacts.
- **FR-027**: The web application MUST allow each user to switch the interface
  language between Chinese and English, update visible UI text immediately
  without a full reload, persist the preference on the user account, apply the
  preference across devices after sign-in, and apply it to navigation, form
  labels, validation messages, empty states, confirmations, and workflow
  feedback without changing authorization behavior.
- **FR-028**: Downloads for papers and code artifacts MUST verify current
  project authorization at request time and MUST record audit-visible download
  events.
- **FR-029**: Paper library imports MUST reject files larger than 50 MB or
  outside PDF, BibTeX, or text metadata formats; code artifact imports MUST
  reject files larger than 200 MB or outside zip or tar.gz archive formats when
  archived, and MUST reject executable-risk or unsupported files in folder
  imports according to project policy. All rejected imports MUST explain the
  violated size or format rule before any file is stored.
- **FR-030**: The login page MUST render as a production screen with a real
  background visual, centered authentication form, accessible labels, loading
  and error states, and no sample-account instructions or placeholder behavior.
- **FR-031**: The codebase, UI copy, seed data commands, and validation guides
  MUST remove prototype descriptions and placeholder implementations from production
  flows; test fixtures may exist only under test scope.
- **FR-032**: The email system MUST support configurable SMTP or development
  email-capture delivery, retry failed sends when safe, mask secrets in logs,
  and expose delivery status for authorized project records.

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
- **UX-006**: Paper and code library screens MUST provide dense searchable lists,
  local folder/file import controls, metadata detail panels,
  duplicate/conflict explanations, import progress, download actions, and
  filtered-empty states.
- **UX-007**: The language switcher MUST be available from the authenticated
  workspace shell, expose accessible Chinese and English labels, update visible
  labels immediately, and preserve keyboard focus and current workflow context
  when changed.
- **UX-008**: The unauthenticated login page MUST keep the form visually centered
  on desktop and mobile and use a production background visual that does not
  interfere with labels, validation errors, or keyboard focus.

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
- **PERF-006**: Paper and code library search/filter MUST complete within 2
  seconds for a project containing up to 1,000 paper records and 250 code
  artifacts.
- **PERF-007**: Duplicate detection for a batch of up to 100 imported paper
  metadata records MUST complete within 10 seconds before files are committed.

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
- **Resource Type**: A configurable professional resource template with custom
  fields, eligibility rules, availability policy, and validation constraints.
- **Resource Item**: A bookable resource instance with name, type, custom field
  values, availability, location, and booking rules.
- **Booking**: A project-scoped reservation for a resource item with requester,
  time window, status, and cancellation or change history.
- **Notification**: An email-triggering event tied to a project record, including
  recipient, reason, delivery status, and relevant action path.
- **Paper Record**: A project-scoped team-library literature item with title,
  authors, venue, year, supplied DOI or external identifiers, tags, abstract or
  notes, local import source, file attachment metadata, checksum, uploader,
  duplicate status, and download history.
- **Code Artifact**: A project-scoped team-library code folder/archive import
  with name, description, version label or commit reference, tags, checksum,
  local import source, file metadata, uploader, status, and download history.
- **User Locale Preference**: An account-level persisted user preference that
  selects Chinese or English interface strings across signed-in devices without
  changing data authorization or stored record language.

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
  reservations for the same configured resource item.
- **SC-007**: At least 90% of pilot users report that project context is clear
  before submitting records, commenting, or booking resources.
- **SC-008**: Project dashboard, project search/filter, and common record update
  actions meet the performance targets stated in this specification for the
  supported project size.
- **SC-009**: Paper local-folder import duplicate-handling tests prevent 100% of
  duplicates within a project for file checksum, supplied DOI or external
  identifier, and normalized title plus first-author plus year matches, and each
  duplicate response names the strongest matching rule used.
- **SC-010**: Authorized users can search paper and code assets in a project
  with up to 1,000 paper records and 250 code artifacts within 2 seconds, while
  unauthorized download attempts for unrelated or removed memberships are
  rejected 100% of the time and create no file response.
- **SC-011**: Code local-folder import validation rejects 100% of duplicate
  version labels or commit references within the same project across active,
  archived, and superseded artifacts, and returns a user-visible conflict reason
  before a new version is stored.
- **SC-012**: After a signed-in user changes the interface language, the
  visible interface updates immediately, the selected Chinese or English
  preference persists on the account, and the preference is observed in a later
  signed-in session on another device or browser without changing the current
  route authorization or stored research content.
- **SC-013**: The login page passes desktop and mobile visual/layout checks with
  a centered form, background visual, accessible fields, production error
  handling, and no sample account copy.
- **SC-014**: Automated checks confirm no production UI copy, management command,
  or business flow refers to placeholder behavior, while test fixtures remain isolated
  to test scope.

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
- Paper and code files are imported from user-selected local folders or files
  into managed application attachments or object-storage references; this
  feature requires metadata, authorization, duplicate detection, and download
  controls regardless of the final storage backend.
- Paper metadata imported from local BibTeX/text metadata or manually supplied
  fields can be edited by authorized users when imported metadata is incomplete
  or inaccurate.
- Chinese and English interface strings are maintained by the application; user
  generated research content is not automatically translated.
- Browser folder selection exposes local filenames and relative path labels to
  the app, but the app cannot keep watching local folders after import unless a
  future desktop agent or sync service is specified.

## Scope Decisions

- This feature covers project-scoped research operations: projects, tasks,
  draft/report submissions, inline review comments, resource bookings,
  notification delivery records, paper library records, code artifacts,
  user locale preference, and the role-aware frontend workflows needed to
  complete those tasks.
- Paper library scope includes local folder/file import, metadata import,
  duplicate detection, search of indexed team-library records, project-scoped
  file download, tags, and audit events. Default automatic online search, PDF
  reader annotations, citation formatting engines, EndNote export, and
  automatic full-text translation remain out of scope.
- Code library scope includes local folder/archive import and download of
  project code with descriptions, version labels, search, checksums, and audit
  events. Hosted Git service replacement, server-side repository diff browsing,
  merge requests, CI execution, and WebSocket real-time collaboration remain out
  of scope.
- WebSocket real-time delivery remains out of scope; the existing request/refresh
  and notification delivery model is sufficient for these planned workflows.
- The frontend implementation must be production-grade React/Vite application
  architecture using Tailwind CSS and shadcn/ui as the design-system foundation,
  including a centered background login screen and no sample-facing product copy.
  TanStack Query remains the server-state layer for Django REST contracts; Redux
  Toolkit and RTK Query remain out of scope unless a future feature identifies
  complex client-only state that TanStack Query and local component state cannot
  handle.
