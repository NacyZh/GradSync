# Feature Specification: Dashboard Calendar and Scheduling

**Feature Branch**: `[spec/feature-015]`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "下一步业务需要为在dashboard功能区构建一个日历与日程功能区，兼顾课题组成员以及个人的日程通知、规划与发布"

## 1. Business Background, User Roles, and Core Goals *(mandatory)*

**Business Background**: Research-group schedules are currently distributed
across project tasks, report cycles, resource bookings, informal messages, and
personal planning tools. Members can miss meetings or deadlines because there
is no single dashboard view showing what applies to the whole group, selected
project members, and the signed-in user. The dashboard needs a calendar that
supports private planning, controlled publication, and timely notifications
without duplicating the existing notification center.

**User Roles**:

- **Student**: Views group and project schedule items addressed to them, sees
  relevant system-derived deadlines and bookings, and creates, updates, or
  deletes only their own private schedule items.
- **Teacher / Advisor**: Has all student calendar capabilities and can publish,
  update, or cancel group schedule items for selected projects or selected
  existing accounts. Teachers manage only group items they published unless
  separately authorized.
- **Administrator**: Uses the combined calendar for operational supervision,
  can publish and manage group schedule items across the workspace, and can
  inspect delivery and publication outcomes. Private personal item details
  remain private to their owner.

**Core Goals**:

- Give every authenticated user one dashboard calendar that clearly separates
  private, group-published, and system-derived schedule items.
- Let teachers and administrators plan and publish recurring or one-time group
  activities to the correct existing members without exposing private plans.
- Turn schedule creation, changes, cancellations, and reminders into relevant
  in-app notifications while keeping immediate operation feedback in the global
  toast surface.
- Reduce missed meetings, deadlines, report periods, and bookings by bringing
  existing time-sensitive work into the same personal agenda.

## Clarifications

### Session 2026-07-20

- Q: What does publishing to all research-group members mean? → A: Group
  publication targets selected project memberships or selected existing
  accounts only; platform-wide all-member broadcast is not supported.
- Q: Which delivery channels should schedule events use? → A: Publication and
  ordinary changes use in-app notifications only; due reminders and
  cancellations use both in-app notifications and email.
- Q: How should existing recurring schedules react to project membership
  changes? → A: Future occurrences use the current project membership: new
  members are added automatically and removed members stop receiving future
  visibility and reminders; historical records remain unchanged.
- Q: How should future periodic progress-report dates be generated? → A: A
  teacher or administrator configures the weekly report weekday and deadline
  time per project; configured projects generate future member report schedule
  items and unconfigured projects generate none.
- Q: Which accounts may staff select directly as schedule recipients? → A:
  Teachers may select only active members of projects they can manage;
  administrators may select any active account.

## 2. Complete Positive Business Flows *(mandatory)*

### User Story 1 - View a Unified Dashboard Calendar (Priority: P1)

An authenticated user opens the dashboard and sees a calendar and upcoming
agenda containing their private items, published items addressed to them, and
relevant system-derived project deadlines, task due dates, report periods, and
resource bookings.

**Why this priority**: A trustworthy consolidated view is the base capability;
planning and publication have little value if members still need to inspect
several modules to understand their schedule.

**Independent Test**: Seed one item from each supported source for a user and
unrelated items for another user, then verify day, week, month, and agenda views
show only the authorized items with their source and status distinguishable.

**Acceptance Scenarios**:

1. **Given** a user has private, group, project, task, report, and booking items,
   **When** the dashboard calendar opens, **Then** all relevant items appear in
   the correct dates and unrelated or unauthorized items do not appear.
2. **Given** multiple items occur on the same day, **When** the user selects that
   day or an item, **Then** a stable detail area shows title, time, source,
   organizer, audience summary, status, and an authorized path to the related
   business record.
3. **Given** the user changes calendar view or navigates to another period,
   **When** items load, **Then** the selected period and view remain usable
   without clipping, overlap, or loss of keyboard focus.
4. **Given** a project's weekly report weekday and deadline time are configured,
   **When** an active project member views a future calendar period, **Then** the
   relevant report deadlines appear as read-only project report items; an
   unconfigured project contributes no assumed future report deadline.

---

### User Story 2 - Plan a Private Schedule (Priority: P1)

Any authenticated user creates a private one-time or recurring schedule item,
updates it, marks it complete when appropriate, or deletes it after confirmation.
Only the owner can view its details or change it.

**Why this priority**: Personal planning lets members turn group obligations and
research work into an actionable agenda without publishing unfinished plans to
the research group.

**Independent Test**: Create, edit, complete, and delete private one-time and
recurring items as each role, then verify another normal user and an
administrator cannot read the private title, description, or reminder details.

**Acceptance Scenarios**:

1. **Given** an authenticated user is viewing the calendar, **When** they create
   a valid private item with date, time, recurrence, and reminder choices,
   **Then** the item appears only on that user's calendar and success is shown
   through the global toast surface.
2. **Given** a recurring private item exists, **When** its owner edits or deletes
   one occurrence or the remaining series, **Then** the selected scope is
   applied and unaffected occurrences remain unchanged.
3. **Given** another user or administrator attempts to open a private item,
   **When** authorization is evaluated, **Then** no private item content is
   disclosed.

---

### User Story 3 - Publish a Group Schedule (Priority: P1)

A teacher or administrator publishes a one-time or recurring activity such as a
group meeting, seminar, milestone, defense, or deadline to selected project
memberships or selected existing accounts.

**Why this priority**: Group scheduling is the main coordination gap and must
target the right members without free-form addresses or accidental broad
publication.

**Independent Test**: Publish an item to each supported audience scope, verify
the member selector uses existing eligible accounts, and confirm only resolved
recipients can see the item and receive its notification.

**Acceptance Scenarios**:

1. **Given** a teacher or administrator creates a group item, **When** they
   choose an audience, **Then** they can select one or more visible projects or
   multiple eligible existing accounts from a searchable dropdown rather than
   entering raw identifiers or broadcasting to every platform account.
2. **Given** a teacher searches direct account recipients, **When** options are
   returned, **Then** only active members of projects that teacher can manage
   appear; an administrator may search any active account.
3. **Given** a valid audience and schedule are selected, **When** the publisher
   confirms publication, **Then** the item appears on each resolved recipient's
   calendar and an in-app publication notification appears in the existing top
   notification center without sending publication email.
4. **Given** a student opens the calendar, **When** group publishing controls are
   rendered, **Then** those controls are absent and direct publication attempts
   are rejected.

---

### User Story 4 - Change or Cancel Published Activities (Priority: P2)

An authorized publisher updates timing, content, audience, or recurrence, or
cancels a published activity. Affected members see the current state and receive
a change or cancellation notification.

**Why this priority**: Research schedules change frequently; stale meeting
details are more harmful than missing convenience features.

**Independent Test**: Update and cancel single and recurring group items while
adding and removing recipients, then verify visibility, history, and
notifications converge to the latest authorized state.

**Acceptance Scenarios**:

1. **Given** a published item exists, **When** its teacher publisher or an
   administrator updates it, **Then** all current recipients see the latest
   details and affected recipients receive one in-app change notification
   without receiving ordinary-change email.
2. **Given** an audience change removes recipients, **When** the change is
   published, **Then** removed recipients no longer see future private details
   for that item and receive a concise removal or cancellation notice.
3. **Given** a published item is cancelled after confirmation, **When** members
   view the relevant period, **Then** the item is visibly cancelled rather than
   silently disappearing, and affected members receive both an in-app
   cancellation notification and email.
4. **Given** a recurring item targets a project, **When** active project
   membership changes, **Then** future occurrences and reminders automatically
   include new members and exclude removed members without changing historical
   occurrences, notifications, or audit records.

---

### User Story 5 - Receive Relevant Schedule Reminders (Priority: P2)

Users receive in-app and email reminders for calendar items addressed to them
according to the item's reminder policy and their permitted preferences.
Selecting an in-app reminder opens the calendar item or its related business
record.

**Why this priority**: A calendar reduces missed work only when upcoming items
surface at the point where users already receive workflow notifications.

**Independent Test**: Configure several reminder offsets, process eligible
items, and verify each recipient gets no more than one reminder per item and
offset with a valid authorized action path.

**Acceptance Scenarios**:

1. **Given** an upcoming item has a reminder, **When** its reminder window is
   reached, **Then** each active authorized recipient receives one in-app
   notification and one email with time, organizer, and a valid action path.
2. **Given** a user follows a schedule notification, **When** the target remains
   available, **Then** the dashboard opens the corresponding date and item or
   the linked business record.
3. **Given** an item is cancelled, completed, expired, or no longer visible to a
   recipient, **When** reminder processing runs, **Then** no obsolete reminder
   is delivered.

## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*

- An item ending before it starts, a recurrence without an end boundary, an
  unsupported reminder offset, or an empty group audience is rejected while
  preserving valid form values for correction.
- All-day and timed items remain correctly assigned to the intended local date
  across month boundaries and daylight-saving or timezone differences.
- A removed, suspended, archived, or otherwise ineligible account cannot be
  newly selected as a recipient; changes in account or project membership are
  resolved before future occurrences or reminders are delivered. New active
  members of a selected project join future occurrences automatically, while
  removed members lose future visibility; historical records remain unchanged.
- Publishing to overlapping project and account audiences produces one visible
  item and one notification per resolved recipient, not duplicates.
- Simultaneous edits use the latest accepted version; a stale editor is warned
  and must review current details before overwriting them.
- Schedule overlap produces a non-blocking conflict warning with the conflicting
  time range; it does not override resource-booking conflict rules or prevent a
  user from intentionally scheduling parallel activities.
- When calendar loading fails, the last successfully loaded period remains
  visible with a stale indication and retry path; forms in progress are not
  cleared.
- When notification delivery is delayed or fails, the calendar item remains
  published and visible, delivery status is recorded, and eligible delivery is
  retried without duplicating notifications.
- Deleted source records remove or invalidate their system-derived items without
  leaving a working link to unauthorized or missing content.
- A project without a configured weekly report weekday and deadline time
  generates no future report-deadline projection and no report reminder.
- An archived project stops generating new future report deadlines while
  retaining authorized historical report schedule visibility.
- Archived projects retain historical schedule visibility where existing
  project visibility allows it but do not accept new project-scoped publication.
- Private item titles, descriptions, attendees, and reminders are excluded from
  administrator oversight views, logs, and notification content not owned by
  the user.
- On narrow mobile viewports, the calendar switches to a usable compact or
  agenda representation with no overlapping visible text or horizontal page
  overflow.

## 4. Quantifiable Acceptance Criteria *(mandatory)*

- **AC-001**: In role-based tests, 100% of authenticated users can open the
  dashboard calendar; students have 0 working group-publication controls, while
  teachers and administrators can publish to their permitted audiences.
- **AC-002**: For seeded users, 100% of authorized private, group-published, task,
  project milestone, report period, and resource booking items appear in the
  correct calendar period, and 0 unauthorized items or private details appear.
- **AC-003**: In publication tests, 100% of recipients resolve from selected
  visible project memberships or selected eligible existing accounts;
  overlapping scopes produce exactly one recipient entry per user, and no
  platform-wide all-account publication path exists. Project membership changes
  update 100% of future recurring occurrence recipients without rewriting any
  historical occurrence or notification recipient. Teacher direct-account
  searches return 0 accounts outside projects they can manage, while
  administrators may resolve any active account.
- **AC-004**: In create, update, cancel, complete, and delete flows, 100% of
  immediate success or failure feedback appears in the global bottom-right
  toast surface and no operation result is embedded inside the form.
- **AC-005**: In notification tests, eligible publication, change, cancellation,
  and reminder events appear in the existing top notification center within 5
  minutes of eligibility; only cancellation and reminder events also produce
  email, with no more than one notification per channel, recipient, item, and
  event occurrence.
- **AC-006**: Across supported desktop, tablet, and 390-pixel mobile validation
  widths, the calendar and agenda produce 0 unintended horizontal page overflow,
  clipped primary actions, or visible text overlaps.
- **AC-007**: At least 95% of month, week, day, and agenda period changes display
  their relevant items within 2 seconds under normal validation conditions with
  500 users and 10,000 schedule occurrences in the tested period.
- **AC-008**: In concurrency tests, 100% of stale update attempts are rejected or
  explicitly reconciled before newer accepted schedule details can be
  overwritten.
- **AC-009**: In privacy tests, 0 non-owners, including administrators, can read
  the title, description, recurrence, or reminder details of another user's
  private item through list, detail, notification, direct, or audit interfaces.
- **AC-010**: In a moderated validation with at least 10 representative users,
  at least 90% can identify today's obligations, create a private item, and, for
  staff roles, publish a group item to the intended audience without assistance.
- **AC-011**: 100% of published item creation, audience changes, schedule changes,
  cancellation, and privileged administrator actions retain auditable actor,
  target scope, outcome, and timestamp information without private personal
  item content.
- **AC-012**: In project report-schedule tests, 100% of active projects with a
  configured weekly weekday and deadline time generate the correct future
  member report deadlines, while 0 unconfigured or archived projects generate
  new future report deadlines.

## 5. Dependencies, Assumptions, and Unsupported Scope *(mandatory)*

### Dependencies and External Systems

- Existing authenticated accounts, active role assignments, and account status
  determine calendar access and publication authority.
- Existing project visibility and membership records determine project-scoped
  audience options and system-derived project items.
- Existing tasks, project dates, progress reports, project-level weekly report
  schedule settings, and resource bookings provide read-only business schedule
  sources and authoritative action paths.
- Existing in-app notification center, delivery records, and reminder processing
  provide schedule publication and reminder visibility.
- Existing email delivery provides the additional cancellation and due-reminder
  channel; publication and ordinary schedule changes do not send email.
- Existing audit behavior provides accountability for group publication and
  administrator actions.

### Business Assumptions

- "Teacher" maps to the existing advisor role used by GradSync.
- "Research group members" means members resolved through selected visible
  projects or selected existing accounts. It does not mean every active
  GradSync account, and this release does not introduce a new organizational
  hierarchy.
- For teachers, a selected existing account must be an active member of a
  project the teacher can manage. Administrators may select any active account
  for operational publication.
- Personal items are private by default and cannot be converted to group items
  without an explicit publish action and audience confirmation.
- System-derived items remain owned by their source module; calendar users open
  the source record to perform business-specific changes.
- Each active project may have one optional weekly progress-report schedule set
  by an authorized teacher or administrator. It includes weekday, local deadline
  time, and timezone; no platform default is assumed when it is absent.
- Calendar dates use the signed-in user's configured timezone when available and
  the workspace timezone otherwise.
- Group reminders use publisher-selected supported offsets; users may mute
  optional reminders but cannot suppress mandatory cancellation or critical
  deadline notices required by existing policy.
- Schedule publication and ordinary changes are in-app-only; cancellation and
  due reminders use both in-app notification and email.
- Project-scoped recurring audiences are dynamic for future occurrences. New
  active project members are included and removed members are excluded, while
  historical occurrence, notification, and audit records remain immutable.
- Explicitly selected account audiences do not automatically gain unrelated
  accounts; selected accounts are removed from future delivery if they become
  inactive or otherwise ineligible.

### Included Scope

- Dashboard calendar with month, week, day, and upcoming agenda views.
- Private one-time, all-day, and bounded recurring schedule items.
- Teacher and administrator publication to selected visible projects or
  multiple eligible existing accounts.
- Group item update, audience change, occurrence/series edit, and confirmed
  cancellation with revision history.
- Read-only calendar projections for project dates, assigned task deadlines,
  configured future report deadlines, submitted report periods, and resource
  bookings relevant to the current user.
- Teacher/administrator configuration of one weekly report weekday, deadline
  time, and timezone per active project.
- In-app publication, update, cancellation, and reminder notifications integrated
  with the existing top notification button, plus email for cancellation and
  due reminders only.
- Global toast feedback for schedule operations, responsive and accessible
  calendar behavior, authorization, audit, degradation, and performance controls.

### Unsupported / Out of Scope

- External calendar synchronization, subscription feeds, meeting links, video
  conferencing, room booking, or automatic email invitation attachments.
- A new research-group organization tree, departments, cross-tenant federation,
  platform-wide all-account broadcast, public anonymous calendars, or
  publication to arbitrary email addresses.
- Attendance roll call, mandatory RSVP workflows, timesheets, workload scoring,
  or automated meeting-minute generation.
- Editing tasks, project dates, reports, or resource bookings directly inside
  calendar forms; those changes remain in their owning modules.
- Multiple report cadences per project, per-student report cadences, and inferred
  report deadlines for projects without an explicit weekly configuration.
- Exposing one user's private personal planning details to teachers,
  administrators, project members, or other users.
- Guaranteed reminder delivery while the notification service or user network is
  unavailable; recorded retry and visible delivery status are required instead.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST provide an authenticated calendar and upcoming
  agenda entry for administrators, teachers/advisors, and students.
- **FR-002**: The calendar MUST combine authorized private items, group-published
  items, and system-derived project, task, report, and booking items without
  changing ownership of source records.
- **FR-003**: Users MUST be able to navigate month, week, day, and agenda views,
  select an item, and see an authorized detail view with source and status.
- **FR-004**: Every authenticated user MUST be able to create, update, complete,
  and delete their own private one-time, all-day, or bounded recurring items.
- **FR-005**: Teachers and administrators MUST be able to publish one-time,
  all-day, or bounded recurring group items; students MUST NOT be able to publish
  group items.
- **FR-006**: Group publication MUST support selected visible projects and
  multiple eligible existing account recipients through searchable dropdown
  selection without raw identifier entry and MUST NOT provide a platform-wide
  all-account publication option. Teacher account options MUST be limited to
  active members of projects the teacher can manage; administrator options MAY
  include any active account.
- **FR-007**: Audience resolution MUST deduplicate recipients and revalidate
  account status, role, and project visibility when publication, future
  occurrences, or reminders occur. Project-scoped recurring audiences MUST add
  new active project members and remove departed members for future occurrences
  without rewriting historical occurrence or delivery records.
- **FR-008**: Authorized publishers MUST be able to update or cancel one
  occurrence, the current and future occurrences, or an entire recurring series
  after confirming the intended scope.
- **FR-009**: The calendar MUST preserve revision and cancellation history for
  published items and show only the current effective state in the primary view.
- **FR-010**: System-derived items MUST link to the authorized source record and
  MUST be read-only in calendar editing controls.
- **FR-011**: The system MUST warn about overlapping visible schedule items
  without treating ordinary overlap as a hard conflict.
- **FR-012**: Publication, material schedule changes, cancellation, and eligible
  reminder windows MUST create in-app notification events for current resolved
  recipients with an authorized action path; cancellation and due-reminder
  events MUST additionally use email, while publication and ordinary changes
  MUST NOT send email.
- **FR-013**: Schedule notifications MUST reuse the existing top notification
  center; immediate operation feedback MUST use the global bottom-right toast
  and MUST NOT be rendered as form-local status text.
- **FR-014**: Users MUST be able to choose supported reminder offsets for items
  they own or publish, subject to mandatory notification policy.
- **FR-015**: Calendar list and detail results MUST converge after create,
  update, cancel, source-record, membership, and account-status changes without
  requiring a full page reload during a normal connected session.
- **FR-016**: Teachers and administrators MUST be able to configure one weekly
  progress-report weekday, local deadline time, and timezone per active project;
  the calendar MUST generate future report deadlines only for configured active
  projects and their current authorized members.

### Security & Privacy Requirements

- **SEC-001**: Every calendar list, detail, create, update, delete, publish,
  cancel, audience-search, and notification action MUST enforce authenticated
  role, ownership, project visibility, and recipient authorization.
- **SEC-002**: Students MUST NOT access group publication operations, and teachers
  MUST NOT modify another teacher's published item unless separately authorized;
  administrators retain workspace supervision authority for group items.
- **SEC-003**: Private personal item content MUST be visible only to its owner and
  MUST remain excluded from administrator supervision, recipient search, group
  notifications, and content-bearing audit records.
- **SEC-004**: Recipient selectors MUST expose only identity information needed
  to distinguish eligible existing accounts, MUST limit teacher results to
  active members of projects the teacher can manage, and MUST not leak unrelated
  accounts or private profile data; administrator search remains limited to
  active accounts and operationally necessary identity fields.
- **SEC-005**: The system MUST record auditable events for group publication,
  audience changes, schedule changes, cancellation, and privileged administrator
  actions while minimizing recorded personal content.

### User Experience Requirements

- **UX-001**: The calendar MUST be integrated into the existing dashboard work
  area and follow current dashboard spacing, navigation, card, notification, and
  role-aware action patterns.
- **UX-002**: Private, group-published, and system-derived items MUST be
  distinguishable through accessible labels and restrained visual treatment that
  does not rely on color alone.
- **UX-003**: Schedule forms MUST provide clear date, time, all-day, recurrence,
  audience, reminder, and confirmation controls while showing only controls the
  current role can use.
- **UX-004**: The calendar, item selector, audience dropdown, recurrence controls,
  detail view, and notification paths MUST be keyboard operable and have
  assistive labels.
- **UX-005**: Loading, empty, stale, conflict, success, warning, and error states
  MUST preserve the selected calendar period and valid in-progress form input.
- **UX-006**: At narrow viewports the dashboard MUST present a compact calendar
  or agenda without horizontal page overflow, visible text overlap, or hidden
  primary actions.
- **UX-007**: The calendar workspace MUST keep period navigation and view
  selection visually distinct, place source filters in a compact menu, bound
  month-cell item density, and use the secondary region for upcoming items or
  the selected item detail instead of persistent instructional empty space.

### Performance Requirements

- **PERF-001**: Calendar period and agenda changes MUST display relevant items
  within 2 seconds in at least 95% of normal sessions.
- **PERF-002**: The calendar MUST remain usable with 500 users and 10,000
  occurrences in a requested period through bounded period queries and bounded
  recipient selection results.
- **PERF-003**: Eligible schedule notifications MUST be recorded or queued within
  5 minutes of their configured reminder window under normal operation.

### Operational Requirements

- **OPS-001**: Existing health and readiness behavior MUST be preserved, and
  operational signals MUST distinguish schedule publication failure, reminder
  delay, audience-resolution failure, authorization denial, stale updates, and
  notification retry without logging private item content.
- **OPS-002**: Deployment and rollback MUST preserve existing project, task,
  report, booking, notification, and audit records and MUST not broaden calendar
  visibility after rollback.
- **OPS-003**: Schedule reminder processing MUST be idempotent and retryable so a
  repeated processing attempt cannot create duplicate recipient notifications.

### Key Entities

- **Schedule Item**: A private or group-published planned activity with title,
  description, start, end, all-day state, timezone, recurrence, status, owner,
  organizer, and reminder policy.
- **Schedule Occurrence**: One effective instance of a one-time or recurring
  schedule item, including exceptions, completion, or cancellation state.
- **Schedule Audience**: The publication scope defined by selected projects or
  selected eligible accounts and its deduplicated resolved recipients.
- **Schedule Revision**: An accountable record of changes to a published item's
  timing, content, audience, recurrence, or status.
- **System Schedule Projection**: A read-only calendar representation of an
  authorized project milestone, task deadline, report period, or resource
  booking that retains a path to its owning record.
- **Project Report Schedule**: An optional project-owned weekly weekday, local
  deadline time, and timezone configuration used to generate future progress
  report deadlines for current project members.
- **Schedule Notification**: A publication, update, cancellation, or reminder
  event for one resolved recipient with delivery state and an authorized action
  path.

## Specification Review and Clarifications *(mandatory)*

**Required Reviewers**:

- Product: Pending
- Testing: Pending
- Development: Pending

Implementation evidence (2026-07-20): automated backend, frontend, security,
performance, accessibility, responsive-layout, and schedule full-stack checks
have been recorded in `quickstart.md`. This evidence does not replace required
human acceptance. Production release remains blocked while any reviewer above
is Pending and no governed release exception is recorded.

**Open Questions**:

- None

**Closed Clarifications**:

- 2026-07-20: The calendar is part of the dashboard work area and includes an
  upcoming agenda; it is not a second notification center.
- 2026-07-20: Students manage private items and view addressed group/system
  items but cannot publish group schedules.
- 2026-07-20: Teachers publish and manage their own group items; administrators
  supervise and manage all group items while other users' private items remain
  private.
- 2026-07-20: Group audiences resolve only from selected visible project
  memberships or selected eligible existing accounts. Platform-wide
  all-account broadcast and a new organization hierarchy are out of scope.
- 2026-07-20: Immediate operation results use the global bottom-right toast;
  publication and reminder events use the existing top notification center.
- 2026-07-20: Publication and ordinary schedule changes are in-app-only;
  cancellation and due reminders additionally send email.
- 2026-07-20: Project-scoped recurring audiences follow current membership for
  future occurrences; membership changes never rewrite historical occurrences,
  notifications, or audit records.
- 2026-07-20: Future progress-report deadlines come only from an explicit
  project-level weekly weekday, deadline time, and timezone configured by a
  teacher or administrator; unconfigured projects generate none.
- 2026-07-20: Teacher direct-account recipient search is limited to active
  members of projects that teacher can manage; administrators may select any
  active account using minimized identity fields.
- 2026-07-20: Existing task, project, report, and booking dates appear as
  read-only calendar projections and remain editable only in their owning
  modules.
