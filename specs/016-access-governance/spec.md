# Feature Specification: Access and Release Governance

**Feature Branch**: `spec/feature-016`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "补齐账号找回与安全生命周期、项目协作角色闭环、管理员审计控制台和规格验收治理。"

## 1. Business Background, User Roles, and Core Goals *(mandatory)*

**Business Background**: GradSync already supports email registration, project
membership, role-aware workspaces, privileged account activation, and audit
event capture. Four governance gaps remain. Users who lose credentials cannot
recover access without manual intervention. Project membership records mention
reviewers and observers, but staff collaborators cannot be consistently added,
removed, reassigned, or constrained by a complete permission model.
Administrators cannot inspect recorded security and business events through the
application. Finally, specifications can remain in a draft or pending-review
state while code proceeds toward release, so stakeholder acceptance is not a
reliable release gate.

This feature closes those gaps as one access-governance lifecycle. Recovery must
restore control of an account without activating suspended, archived, or
unapproved privileges. Project collaborator roles must grant only the work each
role needs. Audit evidence must make privileged actions reviewable without
revealing protected content. Feature acceptance must be attributable,
revision-specific, and enforceable before production release.

**User Roles**:

- **Account holder**: Recovers a forgotten password, verifies an email change,
  reviews active sessions, and revokes sessions they no longer trust.
- **Student**: Retains project work access while seeing only collaborator
  information and project content allowed by current project membership.
- **Primary advisor**: Owns a project, assigns project collaborators, transfers
  ownership, and remains accountable for project access.
- **Co-advisor**: Helps manage project work, members, reviews, reports, and
  materials without independently transferring ownership or permanently
  deleting the project.
- **Reviewer**: Reads project overview, tasks, permitted materials, and only
  submissions and comments explicitly assigned to them; submits review feedback
  without seeing unassigned reports or writing or gaining project-management
  permissions.
- **Observer**: Reads general project status, tasks, and permitted materials but
  cannot modify project work or inspect private reports and writing reviews.
- **Administrator**: Supervises account and project access, searches audit
  evidence, exports bounded audit results, and intervenes in project governance
  without silently bypassing authorization or audit.
- **Product reviewer**: Confirms that a specification solves the intended
  business problem and records acceptance or rejection.
- **Testing reviewer**: Confirms acceptance criteria and release validation
  coverage for a specific specification revision.
- **Development reviewer**: Confirms implementation and operational readiness
  against a specific specification revision.
- **Release operator**: Receives an unambiguous release decision based on
  stakeholder acceptances or an approved, time-bounded exception.

**Core Goals**:

- Let legitimate users recover and secure accounts without creating account
  enumeration or privilege-restoration paths.
- Make every supported project collaborator role assignable, removable, and
  enforceable through one explicit permission model.
- Give administrators useful, searchable, privacy-conscious audit evidence for
  privileged and accountability-sensitive activity.
- Make specification acceptance a revision-bound release gate with owned,
  expiring exceptions rather than an advisory text field.

## Clarifications

### Session 2026-07-23

- Q: What project content may a reviewer read? → A: Project overview, tasks,
  permitted materials, and assigned submissions and comments; unassigned
  reports and writing remain hidden.
- Q: What happens when the sole primary advisor becomes ineligible? → A: The
  project enters governance hold; non-destructive work may continue, but
  governance and destructive actions remain blocked until an administrator
  assigns an eligible successor.
- Q: Which specification changes make prior acceptances stale? → A: Changes to
  user stories, boundary scenarios, acceptance criteria, scope, or requirements
  are automatically material; metadata, formatting, and non-normative
  explanatory changes are not.
- Q: Must product, testing, and development acceptance come from different
  people? → A: Each discipline requires a separate decision, but one authorized
  account may hold and complete multiple assigned review disciplines.
- Q: Which accounts may be assigned as project collaborators? → A:
  Co-advisor, reviewer, and observer roles require an active, email-verified,
  approved teacher account; administrators supervise globally without project
  membership.

## 2. Complete Positive Business Flows *(mandatory)*

### User Story 1 - Recover and Secure an Account (Priority: P1)

An account holder who has forgotten a password requests recovery using their
email address. If the account is eligible, the holder receives a single-use,
time-limited recovery instruction, chooses a compliant new password, and
returns to sign-in. The holder can also request an email-address change after
confirming their current credentials, verify the new address before it replaces
the old one, inspect active sessions, revoke one unfamiliar session, or sign
out every other device.

**Why this priority**: Account recovery is required for normal production use,
while session and email controls prevent recovery from becoming a new takeover
or privilege-escalation path.

**Independent Test**: Create active, suspended, archived, pending-email, and
pending-teacher accounts; exercise recovery, email change, session listing, and
session revocation; verify only eligible account holders regain sign-in and no
account status or approved role is elevated by recovery.

**Acceptance Scenarios**:

1. **Given** an active account holder has forgotten their password, **When**
   they request recovery and complete the valid instruction once, **Then** the
   new password works, the old password fails, and previously active sessions
   are revoked.
2. **Given** an email address is unknown, archived, or otherwise ineligible,
   **When** recovery is requested, **Then** the public response is
   indistinguishable from an eligible request and no recovery capability is
   issued to the requester.
3. **Given** an authenticated account holder knows the current password,
   **When** they request a unique new email address and verify it, **Then** the
   new address becomes the sign-in identity and both old and new addresses
   receive an appropriate security notice.
4. **Given** a new email address has not been verified, **When** the account
   holder signs in or receives notifications, **Then** the existing verified
   address remains authoritative.
5. **Given** an account holder sees an unfamiliar active session, **When** they
   revoke it, **Then** that session loses access while the current session
   remains usable.
6. **Given** an account holder chooses to sign out other devices, **When** the
   action is confirmed, **Then** every other active session is invalidated and
   the current session remains active.
7. **Given** a suspended, archived, or pending-role account completes password
   recovery, **When** the holder attempts to sign in, **Then** the prior account
   restriction still applies.

---

### User Story 2 - Govern Project Collaborator Roles (Priority: P1)

A primary advisor opens project membership management and selects an existing
active, email-verified, approved teacher account. The advisor assigns the person
as co-advisor, reviewer, or observer, can later change or remove that role, and
can transfer primary ownership to an eligible advisor. Each collaborator sees
only the project sections and actions allowed by the assigned role.
Administrators supervise the same lifecycle through global authority without
becoming project members, while all changes remain attributable.

**Why this priority**: The current partial role model creates misleading UI and
unreliable authorization. Completing this lifecycle is necessary before
external reviewers or multiple supervisors can safely join projects.

**Independent Test**: Add one account for every project role to two unrelated
projects, exercise every visible read and write action, change and remove roles,
transfer ownership, and confirm permissions update immediately without leaking
content across projects.

**Acceptance Scenarios**:

1. **Given** a primary advisor manages an active project, **When** they search
   active, email-verified, approved teacher accounts and assign one as
   co-advisor, **Then** the co-advisor can manage tasks, student membership,
   reviews, reports, and materials but cannot transfer ownership or permanently
   delete the project.
2. **Given** a primary advisor assigns a reviewer, **When** the reviewer enters
   the project, **Then** they can read project overview, tasks, permitted
   materials, and submissions and comments explicitly assigned to them, without
   seeing unassigned reports or writing or receiving member, task, project, or
   material-management controls.
3. **Given** a primary advisor assigns an observer, **When** the observer enters
   the project, **Then** they can read project status, tasks, and permitted
   project materials but cannot modify data or inspect private reports, writing
   submissions, or review comments.
4. **Given** a collaborator role is changed or removed, **When** the affected
   person next reads or acts on the project, **Then** the new permission set is
   enforced immediately and stale links do not disclose hidden metadata.
5. **Given** a primary advisor needs to leave a project, **When** they transfer
   ownership to an eligible active advisor, **Then** the successor becomes the
   sole primary advisor and the former owner receives the selected remaining
   role or is removed.
6. **Given** no eligible successor has accepted ownership, **When** an attempt
   is made to remove the sole primary advisor, **Then** the action is rejected
   with corrective guidance.
7. **Given** an administrator intervenes in project membership, **When** the
   change is completed, **Then** normal project boundaries still apply to other
   users and the intervention is recorded with actor and reason.
8. **Given** the sole primary advisor becomes suspended, archived, or otherwise
   ineligible, **When** project access is re-evaluated, **Then** the project
   enters governance hold, existing authorized members may continue reading and
   non-destructive work, and governance or destructive actions remain blocked
   until an administrator assigns an eligible successor with a reason.

---

### User Story 3 - Investigate Activity in an Audit Console (Priority: P1)

An administrator opens an audit console, filters events by time, actor, project,
action category, outcome, and target, inspects a single event's safe metadata,
and exports the currently filtered result set for an authorized governance
review. Viewing and exporting audit evidence is itself recorded.

**Why this priority**: Existing event capture has limited operational value when
administrators cannot investigate incidents, access changes, destructive
actions, or notification failures from a usable governance surface.

**Independent Test**: Generate account, project membership, project lifecycle,
file download, review, resource, and release-governance events; search and
export them as an administrator; verify ordering, filters, pagination,
authorization, redaction, and self-auditing.

**Acceptance Scenarios**:

1. **Given** audit events exist across multiple projects and actors, **When** an
   administrator combines supported filters, **Then** only matching events are
   returned in newest-first order with total-result and time-range context.
2. **Given** an administrator opens an event, **When** details are displayed,
   **Then** actor, time, action, target, project, outcome, reason, and correlation
   context are shown where recorded, while secrets and protected file content
   remain absent.
3. **Given** an administrator exports filtered events, **When** the export is
   prepared, **Then** it contains exactly the authorized filter scope, identifies
   its generation context, and does not include hidden credentials or file
   bodies.
4. **Given** a non-administrator attempts to open, search, or export audit
   records, **When** authorization is evaluated, **Then** access is denied
   without revealing event counts or metadata.
5. **Given** an audit-dependent privileged change cannot be recorded, **When**
   the user attempts the change, **Then** the privileged change does not complete
   and the user receives an actionable failure state.

---

### User Story 4 - Enforce Specification Acceptance (Priority: P1)

Product, testing, and development reviewers record decisions against one exact
specification revision. A release operator can see whether all required
decisions are accepted. Any material specification change invalidates earlier
acceptances. When exceptional release pressure exists, an authorized owner may
record a reasoned, time-bounded exception with scope and approver; expired or
incomplete exceptions do not permit release.

**Why this priority**: The project constitution already requires formal review,
but current free-text statuses cannot reliably stop an unaccepted or materially
changed feature from release.

**Independent Test**: Create a feature revision with pending reviews, record
acceptance and rejection decisions, alter the revision, create valid and invalid
exceptions, and verify the automated release decision for every state.

**Acceptance Scenarios**:

1. **Given** a feature specification revision is ready for review, **When**
   product, testing, and development reviewers each accept it, **Then** the
   revision is marked accepted and becomes eligible for later release gates.
2. **Given** one required reviewer is pending or has rejected the revision,
   **When** release eligibility is evaluated, **Then** release is blocked and
   the missing or rejecting review is identified.
3. **Given** all required reviewers accepted an earlier revision, **When** a
   material specification change creates a new revision, **Then** prior
   acceptances are marked stale and the new revision requires review.
4. **Given** a release exception has an owner, approver, business reason,
   bounded scope, and future expiry, **When** release eligibility is evaluated,
   **Then** only the explicitly covered missing acceptance may be bypassed until
   expiry.
5. **Given** an exception is expired, revoked, unapproved, or broader than the
   requested release scope, **When** release eligibility is evaluated, **Then**
   release remains blocked.
6. **Given** a reviewer records or changes a decision, **When** the decision is
   saved, **Then** reviewer identity, decision, revision, timestamp, and optional
   rationale remain available as governance evidence.
7. **Given** one authorized reviewer is assigned more than one review
   discipline, **When** they complete those reviews, **Then** product, testing,
   and development decisions remain separate and independently attributable.

## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*

- Repeated recovery requests for the same or unknown email return the same
  public acknowledgement and are throttled without exposing account existence.
- A recovery instruction that is expired, already used, superseded, malformed,
  or issued before a later password change cannot be reused.
- Two simultaneous valid recovery attempts result in at most one accepted
  password change; all competing instructions become unusable afterward.
- Temporary email-delivery failure leaves a visible queued or failed delivery
  record for authorized operators and permits a bounded retry without issuing
  unlimited active recovery instructions.
- A user requests an email already attached to another current or pending
  account; the change is rejected without exposing the other account.
- A pending email change expires or is cancelled; the current verified email
  remains unchanged and sign-in continues normally.
- Revoking the current session requires explicit sign-out rather than leaving
  the account in a misleading partially authenticated state.
- A session already expired or revoked is shown as inactive and repeated
  revocation is harmless.
- A teacher account is suspended, archived, or loses teacher approval while it
  holds a project role; the account immediately loses project access and its
  membership history remains auditable. If it was the sole primary advisor, the
  project enters governance hold until administrator-led ownership transfer.
- An ownership transfer target becomes ineligible during a concurrent transfer;
  exactly one valid owner remains and the failed requester receives current
  state.
- The same user cannot hold multiple simultaneous active roles in one project.
- A student, pending teacher, suspended teacher, archived teacher, unverified
  account, or administrator is selected for a co-advisor, reviewer, or observer
  role; assignment is rejected without exposing unrelated account data.
- An existing project is nominally owned by an administrator or another
  ineligible account; migration places it in governance hold until an
  administrator transfers ownership to an active, verified, approved teacher.
- Reviewer assignment to a submission does not silently grant access to other
  projects, unassigned writing, private reports, or unrelated comments.
- Observer access never includes destructive actions, member contact export,
  private student writing, or review feedback.
- Archived projects allow governance inspection but reject new membership and
  role changes other than an administrator-led corrective ownership action with
  a reason.
- Audit filters with invalid dates, reversed ranges, unsupported categories, or
  excessive export scope are rejected with corrective guidance.
- An audit event references a deleted or anonymized target; preserved snapshot
  metadata remains readable without reconstructing deleted protected content.
- Audit search or export is temporarily unavailable; ordinary authorized work
  may continue only when its required event can still be recorded, while
  privileged actions that require audit fail closed.
- Multiple administrators investigate the same events concurrently without
  changing or deleting the underlying evidence.
- A reviewer accepts the wrong specification revision; the decision does not
  satisfy the current revision's release gate.
- A reviewer changes a decision from accepted to rejected before release; the
  release decision changes to blocked without losing prior decision history.
- A specification has no named required reviewer for one discipline; it remains
  blocked until reviewer responsibility or a valid exception is recorded.
- One account is assigned multiple review disciplines; each decision remains a
  distinct record and changing one discipline does not alter the others.
- Governance evidence is unavailable or malformed during release evaluation;
  the release fails closed with the affected feature identified.
- Existing specifications without structured acceptance start as unaccepted;
  historical free-text approval is not silently converted into formal
  acceptance.

## 4. Quantifiable Acceptance Criteria *(mandatory)*

- **AC-001**: Eligible account holders can complete password recovery in under
  five minutes excluding user-controlled email delivery delay, and 100% of
  successful recoveries invalidate the old password and all prior sessions.
- **AC-002**: Recovery requests for eligible, unknown, suspended, and archived
  addresses produce indistinguishable public response content and status in
  automated enumeration tests.
- **AC-003**: Expired, reused, superseded, and concurrently consumed recovery
  instructions are rejected in 100% of validation scenarios.
- **AC-004**: An email address changes only after current-credential
  confirmation and successful verification of a unique new address; the old
  address remains authoritative in 100% of incomplete-change scenarios.
- **AC-005**: Users can identify and revoke an individual active session or all
  other sessions in at most three interactions, and revoked sessions lose
  protected access on their next request.
- **AC-006**: Recovery and email changes preserve suspended, archived,
  pending-email, and pending-role restrictions in 100% of role-state tests.
- **AC-007**: Every supported project role can be added, changed, removed, and
  represented consistently in project membership views without duplicate
  active memberships.
- **AC-008**: The role-permission test matrix denies 100% of actions outside the
  primary-advisor, co-advisor, reviewer, observer, student, and administrator
  definitions and allows all actions explicitly assigned to each role.
- **AC-009**: Ownership transfer and concurrent membership tests leave exactly
  one eligible primary advisor in normal operation, never permit voluntary
  removal of the sole owner without a successor, and place 100% of projects
  whose sole owner becomes externally ineligible into governance hold.
- **AC-010**: Removed or downgraded collaborators lose newly forbidden project
  reads and writes on their next request, and stale project links expose no
  hidden project, member, report, or writing metadata.
- **AC-011**: Administrators can filter an audit history containing at least
  100,000 events by time, actor, project, category, outcome, and target, with
  95% of result pages visible within two seconds.
- **AC-012**: Audit detail and export checks detect zero password values,
  verification or recovery secrets, session credentials, uploaded file bodies,
  or unredacted sensitive request payloads.
- **AC-013**: Audit exports match the selected authorized filter scope and
  displayed total count in 100% of bounded export tests.
- **AC-014**: Non-administrators receive no audit event content, event counts,
  exports, or filter suggestions in 100% of authorization tests.
- **AC-015**: Every successful account recovery, email change, session
  revocation, project-role change, ownership transfer, audit export, acceptance
  decision, and release exception produces attributable governance evidence.
- **AC-016**: Release evaluation blocks 100% of feature revisions with a
  missing, rejected, or stale required acceptance unless an active exception
  exactly covers the missing decision and release scope.
- **AC-017**: Changes to user stories, boundary scenarios, acceptance criteria,
  scope, or requirements mark all earlier acceptances stale before the next
  release evaluation in 100% of change-detection tests, while metadata,
  formatting, and non-normative explanatory changes do not.
- **AC-018**: Expired, revoked, unapproved, ownerless, reasonless, or
  scope-mismatched exceptions permit zero releases.
- **AC-019**: Account, membership, audit, and acceptance screens provide
  keyboard-operable controls, labelled fields, focus-visible confirmation
  dialogs, and non-overlapping content at supported desktop, tablet, and mobile
  sizes.
- **AC-020**: At least 90% of representative users complete one recovery, one
  collaborator assignment, or one audit investigation without administrator or
  developer assistance during acceptance testing.

## 5. Dependencies, Assumptions, and Unsupported Scope *(mandatory)*

### Dependencies and External Systems

- Existing email delivery and delivery-status tracking are available for
  recovery, email-change, and security notifications.
- Existing account status, privileged role activation, project membership,
  project authorization, notification, and audit concepts remain authoritative.
- Existing specification files and release automation provide stable feature
  and revision identities for acceptance evaluation.
- Production time synchronization is reliable enough to enforce expiry windows
  for recovery instructions and release exceptions.

### Business Assumptions

- Email is the sole account-recovery channel in this release.
- Public recovery acknowledgement never reveals whether an account exists or
  why it may be ineligible.
- Recovery instructions are single-use and valid for 30 minutes unless a later
  governed policy sets a shorter duration.
- A successful password reset revokes every existing session; the holder signs
  in again with the new password.
- A normal password change from an authenticated current session may preserve
  that session while revoking all others.
- Each project has exactly one primary advisor. Co-advisors are project
  managers but cannot transfer ownership or permanently delete the project.
- Primary-advisor ownership requires an active, email-verified, approved
  teacher account; administrators supervise globally and cannot own projects.
- Reviewers receive access only through explicit project membership and
  submission assignment. Observers receive read-only general project access and
  no private report or writing access.
- Primary advisors and administrators may assign project collaborators;
  administrator interventions require a reason.
- Co-advisor, reviewer, and observer assignments require active,
  email-verified, approved teacher accounts. Administrators supervise through
  global authority and do not become project members.
- Governance hold permits existing authorized reads and non-destructive
  project work but blocks membership, role, ownership, archive, delete, and
  other destructive governance actions until administrator-led transfer.
- Audit records are immutable through ordinary application workflows and are
  retained for at least 365 days unless a stricter institutional policy applies.
- Product, testing, and development acceptance are all required for each
  releasable feature revision.
- Each review discipline has an assigned authorized account. One account may
  hold multiple disciplines, but every discipline retains a separate decision
  and rationale.
- Changes to user stories, boundary scenarios, acceptance criteria, included or
  unsupported scope, or requirements create a material specification revision
  and stale prior approvals. Metadata, formatting, and non-normative
  explanatory changes do not affect acceptance validity.
- Release exceptions require a distinct approver, named owner, business reason,
  exact scope, and expiry no later than 14 days after approval.

### Included Scope

- Forgotten-password request, delivery tracking, single-use recovery, and
  password reset.
- Verified email-address change with current-credential confirmation,
  cancellation, expiry, uniqueness handling, and security notices.
- Active-session inventory, individual session revocation, all-other-session
  revocation, and session lifecycle evidence.
- Project primary-advisor, co-advisor, reviewer, observer, and student role
  definitions; account selection; assignment; role change; removal; ownership
  transfer; governance hold; authorization; notification; and audit.
- Administrator audit history, combined filters, detail inspection, bounded
  export, redaction, pagination, and audit-access evidence.
- Revision-specific product, testing, and development decisions; stale-review
  handling; release eligibility; and time-bounded exception governance.
- Migration of eligible teacher-owned projects to an explicit single primary
  owner, and governance hold for administrator-owned or otherwise ineligible
  projects until ownership transfer, without changing valid student membership.
- Compatibility guidance for existing specifications and free-text review
  statuses, which begin as pending formal acceptance.

### Unsupported / Out of Scope

- Multi-factor authentication, passkeys, security questions, SMS recovery, or
  support-agent identity proofing.
- Social login, institutional single sign-on, or external identity-provider
  federation.
- Changing an account's approved global role through password recovery or email
  change.
- Multiple simultaneous primary advisors, nested project roles, custom
  per-project permission builders, or public guest links.
- Reviewer or observer access without an active GradSync account.
- Reading uploaded file bodies, private writing text, passwords, secrets, or
  authentication credentials from the audit console.
- Editing, deleting, or rewriting audit events through ordinary administrator
  workflows.
- Unlimited bulk audit export, external security-information platform
  integration, or automated incident remediation.
- Replacing human product, testing, or development judgment with automated
  acceptance.
- A general-purpose repository approval product, legal electronic signatures,
  or production deployment orchestration beyond release eligibility checks.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept forgotten-password requests without revealing
  whether the submitted email identifies an eligible account.
- **FR-002**: System MUST issue at most one current, single-use recovery
  instruction per eligible account and invalidate earlier instructions when a
  newer one is issued.
- **FR-003**: System MUST reject recovery instructions that are expired, used,
  superseded, malformed, or invalidated by a later security change.
- **FR-004**: System MUST enforce the current password policy when a recovered
  account chooses a new password.
- **FR-005**: System MUST invalidate the previous password and all existing
  sessions after successful password recovery.
- **FR-006**: System MUST preserve account suspension, archival, email
  verification, and privileged-role activation status throughout recovery.
- **FR-007**: System MUST require current-credential confirmation before
  starting an email-address change.
- **FR-008**: System MUST keep the current verified email active until a unique
  new address is successfully verified, and MUST support expiry and cancellation
  of an unfinished change.
- **FR-009**: System MUST notify the old and new addresses when an email change
  completes and MUST notify the old address when a change is initiated or
  cancelled.
- **FR-010**: System MUST show the account holder active and recently ended
  sessions with enough device, time, and activity context to recognize them,
  without exposing session credentials.
- **FR-011**: System MUST allow an account holder to revoke one session, revoke
  every other session, and explicitly sign out the current session.
- **FR-012**: System MUST define one active project role per member from primary
  advisor, co-advisor, reviewer, observer, or student.
- **FR-013**: System MUST let a primary advisor or administrator search active,
  email-verified, approved teacher accounts and assign co-advisor, reviewer, or
  observer membership, and MUST exclude students, pending or inactive teachers,
  and administrators from those assignment results.
- **FR-014**: System MUST let authorized project governors change or remove
  collaborator roles and MUST update effective access immediately.
- **FR-015**: System MUST enforce the role capabilities described in User Story
  2 for every project list, detail, task, member, report, review, writing,
  material, notification, and destructive action.
- **FR-016**: System MUST allow reviewers to read project overview, tasks, and
  permitted materials, but MUST require explicit assignment before they can
  inspect or act on a submission or its comments and MUST hide unassigned
  reports and writing.
- **FR-017**: System MUST prevent observers from changing project data or
  reading private reports, writing submissions, and review feedback.
- **FR-018**: System MUST maintain exactly one eligible primary advisor during
  normal operation, require ownership transfer before voluntary removal of the
  sole owner, and enter governance hold if external account state makes the
  sole owner ineligible before a transfer.
- **FR-019**: System MUST let the primary advisor transfer ownership to an
  active, email-verified, approved teacher and choose the former owner's
  resulting role or removal.
- **FR-020**: System MUST require a reason for administrator-led project
  collaborator changes and ownership intervention.
- **FR-021**: System MUST notify affected collaborators of assignment, role
  change, removal, and ownership transfer.
- **FR-022**: System MUST provide administrators a paginated audit history
  filterable by time range, actor, project, action category, outcome, and target.
- **FR-023**: System MUST show a safe audit-event detail containing recorded
  actor, time, action, target, project, outcome, reason, and correlation context.
- **FR-024**: System MUST support bounded export of the administrator's current
  authorized audit filter and identify the export time and requesting
  administrator.
- **FR-025**: System MUST record administrator audit searches, detail access,
  and exports as governance events.
- **FR-026**: System MUST prevent ordinary users, advisors, reviewers,
  observers, and students from discovering audit counts, filters, details, or
  exports.
- **FR-027**: System MUST preserve audit records as immutable evidence through
  ordinary application workflows for the governed retention period.
- **FR-028**: System MUST fail an accountability-sensitive privileged change
  when its required audit evidence cannot be recorded.
- **FR-029**: System MUST record product, testing, and development review
  decisions separately against an exact specification revision.
- **FR-030**: System MUST support pending, accepted, and rejected review
  decisions with assigned discipline, reviewer identity, decision time, and
  rationale and MUST allow one authorized account to hold multiple disciplines
  without merging their decisions.
- **FR-031**: System MUST deterministically mark prior acceptances stale when
  user stories, boundary scenarios, acceptance criteria, scope, or requirements
  change and MUST preserve acceptance validity for metadata, formatting, and
  non-normative explanatory changes.
- **FR-032**: System MUST calculate release eligibility from all required
  current-revision decisions and identify every blocking review.
- **FR-033**: System MUST support a release exception only when it has a named
  owner, distinct approver, reason, exact feature and release scope, approval
  time, and future expiry.
- **FR-034**: System MUST reject expired, revoked, unapproved, incomplete, or
  scope-mismatched release exceptions.
- **FR-035**: System MUST preserve acceptance decisions, stale transitions,
  exception decisions, and release evaluations as governance evidence.
- **FR-036**: System MUST treat existing specifications without valid structured
  current-revision decisions as pending formal acceptance.
- **FR-037**: System MUST allow existing authorized reads and non-destructive
  work during governance hold while blocking membership, role, ownership,
  archive, delete, and destructive governance actions until an administrator
  assigns an eligible successor.

### Security & Privacy Requirements

- **SEC-001**: System MUST rate-limit recovery, email-verification, email-change,
  and session-revocation attempts by appropriate account and request context
  without revealing account existence.
- **SEC-002**: System MUST store only non-recoverable representations of
  recovery and email-verification secrets and MUST never display or log those
  secrets after issuance.
- **SEC-003**: System MUST bind recovery and email-change completion to the
  intended account, purpose, current instruction, and expiry to prevent replay
  or cross-purpose use.
- **SEC-004**: System MUST reject unsafe redirect destinations supplied during
  account recovery and return users only to approved GradSync destinations.
- **SEC-005**: System MUST re-evaluate account status, global role activation,
  project membership, collaborator role, and reviewer assignment on every
  protected request.
- **SEC-006**: System MUST prevent a project-role assignment or ownership
  transfer from granting administrator status or changing global account
  approval.
- **SEC-007**: System MUST serialize concurrent password reset, session
  revocation, project-role, and ownership changes so stale requests cannot
  overwrite a newer security state.
- **SEC-008**: System MUST redact passwords, recovery and verification secrets,
  session credentials, authorization data, private request bodies, and uploaded
  file content from audit records, detail views, and exports.
- **SEC-009**: System MUST authorize audit access and export at request time and
  record the requesting administrator and selected scope.
- **SEC-010**: System MUST prevent acceptance authors from approving their own
  release exception and MUST preserve separation between exception owner and
  approver.
- **SEC-011**: System MUST fail release eligibility closed when acceptance or
  exception evidence is missing, malformed, stale, or unavailable.
- **SEC-012**: System MUST record auditable events for recovery issuance and
  completion, email change, session revocation, collaborator and ownership
  changes, audit access and export, review decisions, exceptions, and release
  evaluations without recording associated secrets.
- **SEC-013**: System MUST give administrators project supervision through
  global authority rather than collaborator membership and MUST prevent
  administrator accounts from being assigned co-advisor, reviewer, or observer
  roles.

### User Experience Requirements

- **UX-001**: Experience MUST provide one clear "Forgot password" journey from
  sign-in and show the same acknowledgement for all submitted email addresses.
- **UX-002**: Experience MUST distinguish current, active-other, recently
  revoked, and expired sessions and require confirmation before broad
  revocation.
- **UX-003**: Experience MUST show pending email changes and allow resend or
  cancellation without replacing the current verified email prematurely.
- **UX-004**: Project membership management MUST use searchable account
  selection and explicit role selection rather than displaying an unrestricted
  account list.
- **UX-005**: Project navigation and action controls MUST adapt to effective
  project role without showing controls the user cannot perform.
- **UX-006**: The audit console MUST keep filters visible, use a bounded
  scrollable result region where necessary, and display event detail separately
  from the result list.
- **UX-007**: Audit empty, loading, filtered-empty, unavailable, redacted, and
  export-limit states MUST explain the next permitted action.
- **UX-008**: Review and release-governance status MUST identify the current
  revision, required reviewers, stale decisions, blocking reasons, and exception
  expiry without requiring source-file inspection.
- **UX-009**: All new user-facing text, notifications, validation messages,
  confirmations, and empty states MUST switch completely between Chinese and
  English.
- **UX-010**: Recovery, session, collaborator, audit, and governance controls
  MUST be keyboard operable, have programmatic labels, preserve visible focus,
  and avoid clipped or overlapping primary content.
- **UX-011**: Success and failure feedback for all state changes MUST use the
  existing global feedback surface and MUST not be embedded as transient form
  messages.

### Performance Requirements

- **PERF-001**: Recovery acknowledgement, session inventory, collaborator
  search, and release eligibility MUST be visible within two seconds for 95% of
  normal requests.
- **PERF-002**: Audit filtering MUST meet AC-011 with at least 100,000 retained
  events and no unbounded result page.
- **PERF-003**: Collaborator search MUST remain usable with at least 10,000
  active accounts and return no more than 25 matching options per result page or
  interaction.
- **PERF-004**: A bounded audit export of up to 10,000 matching events MUST
  complete or enter a visible processing state within two seconds and finish
  within 60 seconds under normal production load.
- **PERF-005**: Revoked sessions and removed or downgraded project roles MUST
  lose forbidden access on the next protected request without relying on a user
  refresh interval.

### Operational Requirements

- **OPS-001**: System MUST expose delivery outcome, retry eligibility, and
  failure reason for account-recovery, email-change, and collaborator security
  notices without exposing secret content.
- **OPS-002**: System MUST expose counts and failure signals for recovery abuse
  throttling, failed session revocation, project-role conflicts, audit recording
  failure, audit export failure, and blocked release evaluation.
- **OPS-003**: Existing accounts, approved roles, project owners, students,
  memberships, audit events, and specification files MUST remain usable during
  migration to the new governance records.
- **OPS-004**: Rollback MUST not reactivate revoked sessions, restore removed
  collaborators, discard audit evidence, or convert pending acceptance into
  accepted status.
- **OPS-005**: Existing projects whose current accountable advisor is an active,
  email-verified, approved teacher MUST receive that teacher as explicit primary
  advisor; administrator-owned or otherwise ineligible projects MUST enter
  governance hold until administrator-led ownership transfer.
- **OPS-006**: Existing specifications MUST default to pending structured
  acceptance, and release reports MUST identify every migrated feature that
  still requires review.
- **OPS-007**: Recovery, role enforcement, audit recording, and release
  eligibility MUST have readiness checks that fail closed when required
  security or governance state is unavailable.
- **OPS-008**: Governance evidence and audit exports MUST follow the existing
  backup, restore, retention, and incident-response procedures.

### Key Entities

- **Account Recovery Request**: A time-limited, single-purpose recovery attempt
  associated with an account, issuance context, delivery outcome, expiry,
  supersession, and consumption state; it never exposes the issued secret.
- **Email Change Request**: A pending replacement email, current account,
  verification state, expiry, cancellation, delivery outcomes, and completion
  time while the existing verified email remains authoritative.
- **Account Session**: One authenticated account context with creation, last
  activity, recognizable device context, expiry, revocation time, revocation
  actor, and revocation reason.
- **Project Role Assignment**: The active or historical relationship among a
  project, account, project role, assignment actor, start time, end time, and
  reason.
- **Project Ownership Transfer**: An attributable transition from one primary
  advisor to another, including the former owner's resulting role and the
  transfer reason.
- **Project Governance Hold**: A temporary project state triggered when no
  eligible primary advisor remains, recording the trigger, start time,
  resolution actor, successor, reason, and resolution time while restricting
  governance and destructive actions.
- **Reviewer Assignment**: A bounded relationship granting one active reviewer
  access to a specific submission or review target inside an authorized
  project.
- **Audit Event**: Immutable governance evidence describing actor, time, action,
  target, project context, outcome, reason, correlation context, and a redacted
  snapshot.
- **Audit Export**: A bounded, attributable representation of one authorized
  filter scope with generation time, requester, result count, status, and
  expiry.
- **Specification Revision**: One identifiable version of a feature
  specification against which stakeholder decisions are recorded, including a
  deterministic identity for its normative user stories, boundary scenarios,
  acceptance criteria, scope, and requirements.
- **Acceptance Decision**: A product, testing, or development reviewer's
  pending, accepted, rejected, or stale decision for one exact specification
  revision with assigned discipline, reviewer identity, time, and rationale;
  decisions remain separate when one account holds multiple disciplines.
- **Release Exception**: A separately approved, owned, reasoned, scope-bounded,
  revocable, and expiring permission to bypass specified missing acceptance for
  a particular release evaluation.
- **Release Eligibility Result**: An attributable decision identifying the
  specification revision, current acceptances, applicable exception, blocking
  reasons, evaluation time, and eligible or blocked outcome.

## Specification Review and Clarifications *(mandatory)*

**Required Reviewers**:

- Product: Pending
- Testing: Pending
- Development: Pending

Structured decisions are maintained in `acceptance.json` and bind each
discipline independently to the SHA-256 fingerprint of the normative sections
configured in `.specify/acceptance-policy.json`. Reviewers update only their
assigned decision. A normative edit makes prior accepted decisions stale;
formatting and this review guidance do not. Production remains blocked while
any decision is pending, rejected, stale, or malformed unless an exact-scope,
revision-bound exception has a distinct approver and expires within 14 days.

**Open Questions**:

- None

**Closed Clarifications**:

- 2026-07-23: Account recovery uses verified email only; multi-factor
  authentication and external identity providers are excluded.
- 2026-07-23: Password recovery never changes account status, global role, or
  privileged-role approval and revokes all existing sessions.
- 2026-07-23: Every project has exactly one primary advisor; co-advisors,
  reviewers, and observers use explicit bounded permissions.
- 2026-07-23: Co-advisor, reviewer, and observer roles require active,
  email-verified, approved teacher accounts; administrators supervise globally
  without project membership.
- 2026-07-23: Reviewer access requires both project membership and explicit
  submission assignment; observer access excludes private reports and writing.
- 2026-07-23: Audit event content is immutable and redacted; ordinary
  privileged changes fail when required audit evidence cannot be recorded.
- 2026-07-23: Product, testing, and development decisions are all required per
  material specification revision, with distinct, time-bounded exceptions.
