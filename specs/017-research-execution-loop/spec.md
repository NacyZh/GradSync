# Feature Specification: Research Execution Loop

**Feature Branch**: `spec/feature-017`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "通知业务没有真正闭环；项目只有 Task，缺少里程碑和交付物；周期报告缺少模板与量化分析；项目决策与风险没有沉淀。"

## 1. Business Background, User Roles, and Core Goals *(mandatory)*

**Business Background**: GradSync can already organize projects, tasks,
periodic reports, materials, reviews, calendar events, and in-app
notifications. These capabilities do not yet form a complete research
execution loop. A notification can be displayed or marked read, but the system
does not consistently distinguish delivery, acknowledgement, action, expiry,
and escalation. Tasks capture activity but do not express major research
outcomes or the evidence required to accept them. Periodic reports accept
free-form progress but lack project-owned templates and comparable indicators.
Important decisions and risks remain scattered across comments, reports, and
offline conversations, making later review and handover unreliable.

This feature connects planning, evidence, reporting, governance, and
notification follow-through. Project teams can plan milestones and deliverables,
measure periodic progress without ranking individuals, preserve the reasons
behind decisions, manage risks through resolution, and receive actionable
notifications whose outcomes are visible to authorized project leaders.

**User Roles**:

- **Student**: Views project milestones, owns assigned deliverables, links work
  evidence, submits template-based periodic reports, raises risks, acknowledges
  notifications, and completes actions within granted project permissions.
- **Primary advisor**: Defines the project execution structure, accepts or
  returns deliverables, publishes report templates, reviews quantitative
  project trends, records decisions, triages risks, and supervises unresolved
  notifications.
- **Co-advisor**: Supports the primary advisor in milestones, deliverables,
  reports, decisions, and risks, except for actions reserved by existing
  project governance rules.
- **Reviewer**: Reads execution context and evaluates only deliverables or
  reports explicitly assigned for review and submits an accept-or-return
  recommendation; cannot issue the final deliverable acceptance, manage project
  membership, notification policy, or unrelated private work.
- **Observer**: Reads general milestones, deliverable status, published
  decisions, and non-private risk summaries without changing project work or
  viewing protected report content.
- **Administrator**: Monitors aggregate execution health, delivery failures,
  escalations, and audit evidence across projects; intervenes only through an
  explicit, reasoned, audited governance capability and does not silently edit
  ordinary project content.

**Core Goals**:

- Turn notifications into traceable business outcomes rather than a list of
  messages.
- Organize project work around milestones and accepted deliverables while
  retaining tasks as the day-to-day execution unit.
- Standardize periodic reports by project and provide comparable, explainable
  trend indicators.
- Preserve project decisions and risks as durable, attributable records linked
  to the work they affect.
- Give each role the minimum information and actions required for its project
  responsibilities.

## Clarifications

### Session 2026-07-24

- Q: Who has final authority to accept a deliverable when a reviewer is
  assigned? → A: The reviewer submits an accept-or-return recommendation; the
  primary advisor or co-advisor issues the final acceptance.
- Q: Who controls project reminder and escalation thresholds? → A: The system
  provides defaults, and the primary advisor may adjust project thresholds
  within enforced bounds.
- Q: How are likelihood, impact, and risk severity classified? → A: Likelihood
  and impact each use low, medium, or high, and a fixed, explained 3-by-3 matrix
  derives the risk severity.
- Q: Which response fields may a periodic report template contain? → A: Long
  text, number, percentage, single choice, multiple choice, milestone or
  deliverable progress, and risk or blocker fields.
- Q: When is a report template version locked for a reporting period? → A: The
  version is locked when the reporting period opens, and newer versions apply
  only to reporting periods opened later.

## 2. Complete Positive Business Flows *(mandatory)*

### User Story 1 - Close the Notification Loop (Priority: P1)

A user opens the global notification panel, filters new and actionable items,
follows a notification to its exact business object, and acknowledges or
completes the required action. The notification retains separate delivery,
read, acknowledgement, action, and expiry states. Users can choose supported
channels and quiet hours by notification category. Project leaders can see
bounded aggregate follow-up status for project-owned notifications without
reading another user's unrelated private notifications.

**Why this priority**: Milestones, reports, deliverables, decisions, and risks
cannot be governed reliably if important reminders disappear after being read
or fail without an accountable fallback.

**Independent Test**: Generate informational, acknowledgement-required,
action-required, reminder, escalation, and failed-delivery notifications for
multiple projects and users; verify preferences, unread indicators, deep links,
state transitions, expiry, retry/escalation behavior, and project isolation.

**Acceptance Scenarios**:

1. **Given** a user has a new notification, **When** they open the notification
   panel, **Then** the unread indicator clears only for notifications actually
   displayed as read and each item retains its action status.
2. **Given** a notification requires acknowledgement, **When** the recipient
   acknowledges it, **Then** the acknowledgement time is recorded and the item
   no longer appears in the recipient's pending acknowledgement view.
3. **Given** a notification requires a business action, **When** the recipient
   follows its link and completes that action, **Then** the notification is
   marked completed without requiring a second manual confirmation.
4. **Given** a required action remains incomplete near or beyond its due time,
   **When** the reminder or escalation threshold is reached, **Then** the
   recipient and permitted project leader receive the configured follow-up
   without duplicate active reminders.
5. **Given** a user changes channel preferences or quiet hours, **When** a
   future non-urgent notification is created, **Then** its delivery follows the
   new preference while urgent security notices retain mandatory delivery.
6. **Given** a primary advisor needs a different follow-up cadence, **When**
   they adjust a project threshold within the permitted range, **Then** future
   reminders and escalations use the project value without changing underlying
   due dates or allowing recipients to disable required follow-up.
7. **Given** a primary advisor enters a threshold outside the permitted range,
   **When** they attempt to save it, **Then** the change is rejected with the
   accepted range and the previous effective policy remains active.
8. **Given** an external delivery channel fails, **When** the failure policy is
   applied, **Then** the in-app notification remains available, retry or
   terminal failure is visible to administrators, and the user is not shown a
   false delivered state.
9. **Given** a user opens a stale notification after the target was deleted or
   access was revoked, **When** the link is followed, **Then** no protected
   metadata is revealed and the notification is identified as unavailable.

---

### User Story 2 - Plan Milestones and Accept Deliverables (Priority: P1)

A primary advisor or co-advisor defines a milestone with a target date and
responsible members, adds one or more deliverables with acceptance criteria,
and optionally links existing tasks. Assigned students update deliverable
progress and attach permitted evidence. An authorized advisor reviews each
submitted deliverable, accepts it or returns it with a reason, and the
milestone status is derived from its deliverables rather than manually
claiming completion.

**Why this priority**: Task completion alone cannot show whether a research
stage produced an acceptable proposal, experiment, dataset, manuscript, or
other required outcome.

**Independent Test**: Build a project with multiple milestones, deliverables,
assignees, evidence items, and linked tasks; submit, return, resubmit, accept,
reorder, and archive records; verify status derivation, permissions, history,
calendar visibility, and notification outcomes.

**Acceptance Scenarios**:

1. **Given** an active project, **When** an authorized advisor creates ordered
   milestones and deliverables with owners, dates, and acceptance criteria,
   **Then** all project members see the execution plan permitted by their role.
2. **Given** a task supports a deliverable, **When** it is linked, **Then** the
   task remains independently manageable while its current status contributes
   context and does not automatically prove deliverable acceptance.
3. **Given** an assignee has prepared the expected output, **When** they submit
   the deliverable with required evidence, **Then** the item enters review and
   its assigned reviewer receives an actionable notification.
4. **Given** an assigned reviewer completes an evaluation, **When** they submit
   an accept-or-return recommendation, **Then** the recommendation and rationale
   are preserved for an authorized advisor without completing or reopening the
   deliverable by themselves.
5. **Given** a submitted deliverable does not meet its acceptance criteria,
   **When** the advisor returns it with a reason, **Then** it reopens for
   revision, preserves prior evidence and review history, and notifies its
   assignees.
6. **Given** a reviewer has recommended acceptance or no separate reviewer is
   required, **When** a primary advisor or co-advisor accepts the deliverable,
   **Then** the final acceptance is attributable to that advisor.
7. **Given** every required deliverable in a milestone is accepted, **When**
   milestone status is evaluated, **Then** the milestone is marked completed
   with the completion time derived from the final acceptance.
8. **Given** a milestone target date changes, **When** the change is confirmed,
   **Then** affected project members see the revised date, calendar entries and
   pending reminders are updated, and the former date remains auditable.
9. **Given** a milestone or deliverable has historical activity, **When** it is
   retired, **Then** it is archived rather than silently erased from reports,
   decision links, risk links, and revision history.

---

### User Story 3 - Submit Structured Reports and Analyze Progress (Priority: P1)

An advisor publishes a project-specific periodic report template containing
required narrative prompts, measurable indicators, milestone and deliverable
updates, and risk or blocker prompts. Students submit reports for the scheduled
period using the active template. Advisors return or accept reports through the
existing revision workflow and inspect project and member trends over selected
periods. Every metric remains traceable to its source and is used for project
support, not automatic performance ranking.

**Why this priority**: Free-form reports are difficult to compare over time and
do not provide an early warning when commitments, deliverables, or risks are
drifting.

**Independent Test**: Publish and revise templates, submit reports before and
after a template change, review multiple revisions, create missing and late
periods, and verify historical rendering, required fields, calculations,
filters, exports, permissions, and absence of ranking scores.

**Acceptance Scenarios**:

1. **Given** a project has no custom template, **When** a reporting period
   opens, **Then** a usable default template is available and identifies all
   required responses.
2. **Given** an advisor configures a report template, **When** they add fields,
   **Then** they can choose long text, number, percentage, single choice,
   multiple choice, milestone or deliverable progress, and risk or blocker
   fields, including required status and explanatory labels where applicable.
3. **Given** an advisor publishes a new template version, **When** future
   reporting periods open, **Then** they use the new version while every draft,
   submitted, returned, and in-review report in an already-open period retains
   the version locked when that period opened.
4. **Given** a student completes all required fields and indicators, **When**
   they submit the report, **Then** values are validated, the report enters
   review, and later edits require the return-and-resubmit revision flow.
5. **Given** multiple reporting periods exist, **When** an advisor selects a
   bounded date range, **Then** the analysis shows on-time, late, missing,
   accepted, and returned counts plus milestone, deliverable, and declared
   blocker trends with source links.
6. **Given** an indicator has no data for a period, **When** trends are shown,
   **Then** the value is displayed as unavailable rather than zero or an
   inferred result.
7. **Given** a report is returned and resubmitted, **When** revision history is
   opened, **Then** each submitted revision, review outcome, explanation, and
   template version remains distinguishable.
8. **Given** an authorized user exports a report or aggregate view, **When**
   export completes, **Then** it reflects the selected project, period, and
   permitted data without assigning a hidden productivity score or rank.

---

### User Story 4 - Record Decisions and Manage Risks (Priority: P1)

Project members capture a decision with its context, considered options,
selected outcome, owner, effective date, and links to affected work. Students
and advisors raise risks with likelihood, impact, owner, mitigation, review
date, and current state. Advisors triage risks, record treatment decisions, and
resolve or accept them with rationale. Superseded decisions and closed risks
remain searchable and attributable.

**Why this priority**: Research teams need to understand why a direction
changed and whether known threats were addressed, especially during handover,
review, or project recovery.

**Independent Test**: Create decisions and risks from project work and periodic
reports; revise, link, supersede, triage, escalate, accept, and resolve them;
verify history, role restrictions, reminders, project isolation, and reporting
summaries.

**Acceptance Scenarios**:

1. **Given** a project direction is agreed, **When** an authorized advisor
   records the decision and its rationale, **Then** the decision is attributable,
   searchable, and linkable to affected milestones, deliverables, tasks,
   reports, materials, and risks.
2. **Given** a recorded decision later changes, **When** a replacement decision
   is published, **Then** the old record is marked superseded, both records
   remain readable, and the relationship between them is explicit.
3. **Given** a project member identifies a risk or promotes a report blocker,
   **When** they raise it, **Then** the risk enters triage with source context
   and the responsible advisor receives an actionable notification.
4. **Given** an advisor triages a risk, **When** likelihood, impact, owner,
   treatment, and review date are confirmed, **Then** its severity and next
   action are derived from the fixed 3-by-3 matrix and visible with an
   explanation to permitted project members.
5. **Given** a high-severity or overdue open risk remains unresolved, **When**
   its review threshold passes, **Then** the owner and project leaders receive
   one active escalation and project health reflects the condition.
6. **Given** a risk is accepted or resolved, **When** an authorized advisor
   closes it with rationale and evidence, **Then** reminders stop, closure
   remains auditable, and the risk stays available in historical analysis.
7. **Given** an observer or reviewer accesses project governance records,
   **When** a record includes protected report or material context, **Then**
   only the record summary and linked content permitted by that role are shown.

## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*

- A user reading a notification must not be treated as having acknowledged it
  or completed its underlying action.
- Mark-all-read affects only readable items in the user's current authorized
  notification scope and never completes required actions.
- Duplicate events for the same recipient, category, target, and active
  reminder window produce one active notification while retaining delivery
  attempt history.
- Concurrent acknowledgement or business-action completion is idempotent and
  results in one effective completion record.
- Revoked project access immediately prevents notification deep links,
  deliverable evidence, reports, decisions, and risks from disclosing hidden
  titles, member names, counts, or statuses.
- Quiet hours defer non-urgent channels but do not change the underlying due
  date, read state, or mandatory security delivery.
- If an external notification channel is unavailable, core project work and
  the in-app notification center remain usable; operators can distinguish
  pending retry from terminal failure.
- A milestone cannot be marked complete while a required deliverable is
  unaccepted, returned, blocked, or overdue.
- Removing or deactivating an assignee requires an authorized replacement or
  an explicit unassigned state surfaced to project leaders; ownership is never
  silently transferred.
- A deleted task or material linked as evidence leaves a safe historical
  reference without restoring access to deleted or restricted content.
- A deliverable submitted concurrently with an advisor edit uses one
  unambiguous version; conflicting stale updates are rejected with a refresh
  path rather than overwriting newer work.
- Template changes do not mutate open reporting periods, drafts, or submitted
  revisions; a newer template applies only to periods opened after publication.
- Calculations exclude missing data from denominators unless the metric
  explicitly measures missing submissions, and every aggregate states its
  population and date range.
- Large projects use bounded lists, search, filters, and pagination or
  progressive loading; notification, milestone, deliverable, report, decision,
  and risk surfaces must not expand without limit.
- A report blocker promoted to a risk retains one source relationship and does
  not create duplicate open risks after repeated submission.
- Decisions with downstream references and risks with activity history cannot
  be permanently deleted through ordinary project controls; corrections use
  revision, supersession, archive, or closure.
- If calendar synchronization is temporarily unavailable, authoritative due
  dates remain visible in the project and are reconciled without duplicate
  events when service resumes.
- If aggregate analysis cannot be calculated, source reports remain usable and
  the affected metric shows an unavailable state with a retriable explanation.
- Offline cached views may expose only data previously authorized for the
  current account; creating or resolving governance records while offline is
  not guaranteed in this feature.

## 4. Quantifiable Acceptance Criteria *(mandatory)*

- **AC-001**: Automated tests verify independent transitions for delivered,
  read, acknowledged, action-completed, expired, retrying, and failed
  notification states, including idempotent repeated actions.
- **AC-002**: In a test set of 100 mixed notifications, unread and pending-action
  filters return 100% of eligible items and no item from another account or
  project.
- **AC-003**: A completed linked business action updates its actionable
  notification within 5 seconds for 95% of normal interactive requests without
  a full page reload.
- **AC-004**: Channel preference, quiet-hour, mandatory-security, retry, and
  escalation scenarios produce the expected delivery decision in 100% of
  automated policy cases.
- **AC-005**: Every completed milestone in automated scenarios has all required
  deliverables accepted, and no task-only completion can satisfy deliverable
  acceptance.
- **AC-006**: Submission, return, resubmission, acceptance, reassignment, date
  change, archive, and concurrent-edit scenarios preserve 100% of expected
  milestone and deliverable history.
- **AC-007**: For a project with 200 milestones or deliverables, users can find
  a known item through search or filters and open its detail within 3 seconds
  for 95% of measured requests under the production reference load.
- **AC-008**: Historical reports render with the template version used at each
  submission in 100% of template-version migration tests.
- **AC-009**: On-time, late, missing, review outcome, milestone, deliverable,
  and blocker aggregates match independently calculated fixtures exactly,
  including empty and missing-data periods.
- **AC-010**: Every displayed aggregate identifies its project scope, date
  range, population, units, and source records, and no view or export contains
  a member rank or opaque productivity score.
- **AC-011**: Decision supersession and risk triage, escalation, acceptance,
  resolution, and reopening preserve actor, time, rationale, source, and linked
  work in 100% of lifecycle tests.
- **AC-012**: Role-boundary tests cover student, primary advisor, co-advisor,
  reviewer, observer, administrator, removed member, and unrelated user across
  all four capability areas with zero unauthorized reads or writes.
- **AC-013**: Every privileged change, acceptance outcome, template publication,
  decision publication, risk closure, and administrative intervention produces
  one attributable audit event without protected file bodies or secrets.
- **AC-014**: At 390 px and 1440 px viewports, automated checks find no clipped
  primary controls, incoherent text overlap, or unbounded panel growth in the
  notification and project execution journeys.
- **AC-015**: All new user-facing labels, states, validation messages,
  notifications, and exported headings have complete English and Chinese
  variants, with locale checks reporting zero untranslated fallback keys.
- **AC-016**: When notification delivery, calendar synchronization, or aggregate
  analysis is unavailable, users can still read and update authoritative
  project records and see the degraded state within 5 seconds.
- **AC-017**: In moderated acceptance testing, at least 90% of representative
  advisors can create a milestone, define and assign a deliverable, publish a
  report template, and triage a risk without assistance.
- **AC-018**: In moderated handover testing, at least 90% of representative
  project members can find the accepted evidence, report trend source,
  governing decision, and current mitigation for a named project outcome
  within 2 minutes.

## 5. Dependencies, Assumptions, and Unsupported Scope *(mandatory)*

### Dependencies and External Systems

- Existing account authentication, project membership, collaborator roles, and
  capability enforcement from the access-governance lifecycle.
- Existing projects, tasks, materials, reports, review revisions, calendar,
  global notification panel, bilingual content, and audit event capture.
- Configured email delivery for recipients who enable email or receive
  mandatory security messages.
- Production scheduling and background processing for reminders, retries,
  escalations, and aggregate refresh.

### Business Assumptions

- Each milestone belongs to one project and may contain multiple required or
  optional deliverables in a project-defined order.
- A deliverable may have multiple assignees but has one current review outcome;
  an advisor may assign an eligible reviewer where project policy permits.
- Tasks may link to one or more deliverables, but deliverable acceptance always
  requires explicit evidence and an authorized review outcome.
- One report template version is active for future periods in a project at a
  time; a default template keeps reporting usable before customization.
- A reporting period locks the active template version when the period opens;
  every member report and later revision for that period retains that version.
- Report templates use only long text, number, percentage, single choice,
  multiple choice, milestone or deliverable progress, and risk or blocker
  fields; arbitrary field types and user-defined calculations are unsupported.
- Existing periodic scheduling remains authoritative for report periods.
- Reminder and escalation thresholds have system defaults; a primary advisor
  may adjust project values only within enforced minimum and maximum bounds.
- Likelihood and impact each use low, medium, or high; a fixed, explained
  3-by-3 matrix derives low, medium, or high severity and is not customizable
  by individual projects.
- Notifications belong to recipients, while project leaders see only aggregate
  follow-up status and project-relevant acknowledgement evidence permitted by
  policy.
- One authorized maintainer may later record multiple specification review
  disciplines, but each discipline remains a separate attributable decision.

### Included Scope

- Actionable notification state, preferences, quiet hours, reminders,
  escalation, delivery visibility, and deep-link completion.
- Project milestones, deliverables, acceptance criteria, evidence, review,
  history, task linkage, and calendar linkage.
- Versioned project report templates, structured report responses, revision
  compatibility, bounded trend analysis, and authorized export.
- Decision register, decision supersession, risk register, treatment,
  escalation, closure, history, and links to project work.
- Role-aware project health summaries and audit evidence for the included
  lifecycles.

### Unsupported / Out of Scope

- General-purpose workflow designers, arbitrary notification rule scripting,
  and user-defined automation code.
- Full portfolio finance, grant accounting, procurement, staffing, timesheets,
  and institutional performance appraisal.
- Automatic scientific-quality judgment, automatic deliverable acceptance,
  member ranking, hidden productivity scoring, or disciplinary recommendations.
- Full dependency-network planning, critical-path scheduling, resource
  leveling, and replacement of specialist project-management products.
- Public or cross-organization sharing of private execution records.
- Guaranteed offline creation, review, conflict merging, or notification
  delivery.
- Permanent deletion of attributable decisions, accepted deliverables,
  submitted reports, or risks with governance history through ordinary project
  controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST distinguish notification delivery, read,
  acknowledgement, linked-action completion, expiry, retry, and terminal
  failure without conflating one state with another.
- **FR-002**: System MUST provide a global notification view with unread,
  pending-action, category, project, and time filters plus exact authorized
  links to affected business objects.
- **FR-003**: System MUST let users manage supported notification channels and
  quiet hours by category while preserving mandatory security delivery.
- **FR-004**: System MUST suppress duplicate active reminders and support
  attributable reminders and escalations for overdue required actions.
- **FR-005**: System MUST let authorized advisors create, order, revise,
  archive, and review project milestones and deliverables.
- **FR-006**: System MUST capture deliverable owners, target dates, acceptance
  criteria, required evidence, linked work, status, review outcome, and history.
- **FR-007**: System MUST derive milestone completion from required deliverable
  acceptance and expose overdue, blocked, at-risk, and completed states
  consistently.
- **FR-008**: System MUST allow eligible project members to update assigned
  deliverables and submit evidence without granting project-management powers.
- **FR-009**: System MUST let authorized advisors publish versioned periodic
  report templates with required narrative, quantitative, execution-progress,
  and risk or blocker prompts.
- **FR-010**: System MUST preserve the template snapshot and submitted values
  for every report revision and retain the existing submit, return, revise,
  resubmit, and accept lifecycle.
- **FR-011**: System MUST calculate bounded, source-traceable reporting and
  execution indicators with explicit treatment of missing data.
- **FR-012**: System MUST provide authorized project and member trend views
  without automatic rankings, hidden composite scores, or unsupported
  conclusions.
- **FR-013**: System MUST provide a searchable project decision register with
  context, options considered, outcome, owner, effective date, rationale,
  related work, revision history, and supersession.
- **FR-014**: System MUST let project members raise risks and authorized
  advisors triage, assign, treat, accept, resolve, reopen, and review them.
- **FR-015**: System MUST capture low, medium, or high likelihood and impact,
  derive low, medium, or high severity through one fixed and explained 3-by-3
  matrix, retain source context, and escalate high or overdue open risks.
- **FR-016**: System MUST link milestones, deliverables, tasks, materials,
  reports, decisions, risks, calendar entries, and notifications without
  bypassing the authorization of either linked record.
- **FR-017**: System MUST provide role-appropriate project execution summaries
  showing upcoming commitments, pending reviews, missing reports, open risks,
  and unresolved required actions.
- **FR-018**: System MUST preserve attributable history for state changes,
  acceptance decisions, template versions, report revisions, decision
  supersession, risk treatment, and administrative intervention.
- **FR-019**: System MUST provide bounded search, filtering, ordering, and
  archive access for every potentially large list introduced by this feature.
- **FR-020**: System MUST emit project-scoped follow-up notifications for
  assignments, submissions, returns, acceptances, approaching dates, overdue
  work, report periods, decisions requiring acknowledgement, and risk
  escalation.
- **FR-021**: System MUST treat an assigned reviewer's accept-or-return
  recommendation as advisory and require a primary advisor or co-advisor to
  issue the final deliverable acceptance.
- **FR-022**: System MUST provide default reminder and escalation thresholds,
  let the primary advisor adjust project values within enforced bounds, and
  prevent recipient preferences from disabling required project follow-up.
- **FR-023**: System MUST restrict report templates to long text, number,
  percentage, single choice, multiple choice, milestone or deliverable
  progress, and risk or blocker fields with field-specific validation.
- **FR-024**: System MUST lock one report template version when a reporting
  period opens and retain it for every draft, submission, return, and
  resubmission in that period.

### Security & Privacy Requirements

- **SEC-001**: System MUST enforce current account, project membership,
  collaborator role, assignment, and linked-record permissions on every read,
  write, export, notification, and deep link.
- **SEC-002**: System MUST prevent notification previews, aggregate counts,
  exports, cached views, and historical references from revealing protected
  report content, material metadata, member identity, or project existence to
  unauthorized users.
- **SEC-003**: System MUST record auditable events for notification policy
  changes, escalations, milestone and deliverable acceptance, report template
  publication, report outcomes, decision publication and supersession, risk
  closure, exports, and administrative intervention.
- **SEC-004**: System MUST require a reason and preserve actor identity for
  destructive, superseding, acceptance, closure, and administrative actions.
- **SEC-005**: System MUST apply current authorization immediately after role
  change, removal, suspension, archive, or project deletion and invalidate
  stale action links without metadata leakage.

### User Experience Requirements

- **UX-001**: The experience MUST use the existing global half-screen
  notification panel for notifications and the global lower-right toast for
  transient operation results; forms MUST NOT display duplicate success or
  operation-result banners.
- **UX-002**: Milestone, deliverable, report, decision, and risk workspaces MUST
  use fixed, bounded list-and-detail layouts with search and filters, preserving
  usable dimensions when lists grow.
- **UX-003**: Status controls MUST present only permitted next actions with
  plain-language consequences; history is read separately from current action
  controls.
- **UX-004**: Every included journey MUST provide clear loading, empty,
  validation, conflict, unavailable, retrying, success, warning, and permission
  states in English and Chinese.
- **UX-005**: All controls, filters, timelines, metrics, charts, and linked
  records MUST support keyboard navigation, visible focus, assistive labels,
  non-color status cues, and reduced-motion preferences.
- **UX-006**: Quantitative views MUST show definitions, units, population,
  period, missing-data treatment, and source access near the displayed result.

### Performance Requirements

- **PERF-001**: Opening the notification panel, a project execution list, or a
  selected detail MUST show usable authorized content within 3 seconds for 95%
  of requests under the production reference load.
- **PERF-002**: Status changes and linked notification completion MUST become
  visible to concurrently connected authorized users within 5 seconds for 95%
  of normal requests without a full page reload.
- **PERF-003**: A project containing 200 milestones or deliverables, 500 report
  revisions, 500 decisions or risks, and 1,000 notifications per user MUST
  retain bounded list rendering and complete filtered retrieval within 3
  seconds for 95% of reference-load requests.

### Operational Requirements

- **OPS-001**: System MUST expose health and auditable counts for pending,
  retrying, failed, expired, acknowledged, and action-completed notification
  outcomes without exposing message content.
- **OPS-002**: System MUST expose lag, failure, and last-success signals for
  reminder scheduling, escalation, calendar reconciliation, and aggregate
  calculation.
- **OPS-003**: Deployment MUST preserve existing tasks, reports,
  notifications, and project access, support forward data adoption without
  fabricating historical acceptance, and provide a rollback path that does not
  discard newly recorded governance history.
- **OPS-004**: Retry and reconciliation operations MUST be idempotent, bounded,
  and observable so repeated execution cannot duplicate reminders, calendar
  entries, report periods, decisions, or risks.
- **OPS-005**: Backup and restore validation MUST include notification outcome
  history, milestone and deliverable evidence references, report template
  versions, decisions, risks, and their audit records.

### Key Entities

- **Notification Policy**: A user's channel and quiet-hour choices by
  notification category, including mandatory-delivery exceptions.
- **Notification Outcome**: The recipient-specific delivery, read,
  acknowledgement, linked-action, expiry, retry, and failure history for one
  business notification.
- **Milestone**: An ordered project outcome boundary with owners, target date,
  derived status, and required deliverables.
- **Deliverable**: A reviewable project output with assignees, acceptance
  criteria, evidence, linked tasks, revision history, and review outcome.
- **Report Template Version**: The immutable structure and indicator definitions
  used by reports opened for a defined set of future periods, composed of the
  supported controlled response fields and their validation rules.
- **Reporting Period**: A scheduled project reporting window that locks one
  template version at opening and applies it to every member report and
  revision in that period.
- **Report Response Snapshot**: The narrative and quantitative responses tied
  to one report revision and one template version.
- **Progress Indicator**: A defined, source-traceable value with unit,
  population, period, missing-data rule, and authorized scope.
- **Decision Record**: An attributable project choice with context, options,
  outcome, rationale, effective date, links, and supersession history.
- **Risk Record**: A project uncertainty or threat with source, likelihood,
  impact, severity, owner, treatment, review date, state, and closure history.

## Specification Review and Clarifications *(mandatory)*

**Required Reviewers**:

- Product: NacyeZ / Pending
- Testing: NacyeZ / Pending
- Development: NacyeZ / Pending

**Open Questions**:

- None

**Closed Clarifications**:

- 2026-07-24: Existing project roles and capability boundaries remain
  authoritative; administrators supervise globally and do not become default
  project content owners.
- 2026-07-24: Periodic analysis supports project improvement and early warning;
  individual ranking and opaque productivity scoring are excluded.
- 2026-07-24: Historical reports retain their submitted template version, and
  decisions or risks with activity history use revision or closure rather than
  silent deletion.
- 2026-07-24: Tasks remain the daily execution unit; milestone completion
  depends on explicit acceptance of required deliverables.
