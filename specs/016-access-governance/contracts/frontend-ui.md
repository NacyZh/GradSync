# Frontend UI Contract: Access and Release Governance

## Shared Interaction Rules

- All new user-facing strings have complete English and Simplified Chinese
  translations. API error codes map to localized messages; raw server messages
  are not rendered.
- Mutation success, failure, retry, and conflict feedback uses the existing
  bottom-right global toast system. Forms retain field-level validation only
  for the field that needs correction.
- Searchable account controls are input-driven comboboxes. They do not expose
  the full account directory before the user searches, return at most 25
  options, support keyboard navigation, and identify people by display name,
  nickname, and masked email.
- Loading, empty, unavailable, forbidden, stale, and retry states preserve
  their panel dimensions. Lists scroll inside bounded regions.
- Destructive and session-revocation actions require an explicit confirmation
  dialog naming the affected account, device, role, or project.
- Live project governance changes invalidate the relevant TanStack Query cache
  from project events. A user whose access is removed is redirected to the
  projects list on the next protected operation without leaking project data.

## Account Recovery Routes

### `/forgot-password`

- Public route using the existing authentication shell.
- Contains one email field and a submit action.
- Every syntactically valid request receives the same completion view,
  regardless of account existence, status, or delivery outcome.
- The completion view never displays account status or the submitted address in
  full. Repeated submission respects a visible cooldown without revealing the
  server throttle decision.

### `/reset-password`

- Public route accepts the opaque recovery token from the approved application
  URL only.
- Contains new-password and confirmation fields, password requirements, and a
  submit action.
- Expired, consumed, malformed, and superseded tokens share one non-sensitive
  invalid-link state with a new-recovery action.
- Success invalidates all account sessions and returns the user to sign-in.

## Profile Security

The authenticated profile adds a `Security` section:

- Email change shows the current masked address, requires current password and
  a new address, and clearly marks a pending verification request. Cancel and
  resend remain available outside the form while pending.
- Active sessions use a bounded list with device/browser summary, approximate
  location when available, created time, last-used time, and a `Current`
  indicator.
- Users can revoke one other session or all other sessions. The current session
  cannot be revoked through its row action.
- If the current session becomes invalid, the shared authentication boundary
  clears private caches and redirects to sign-in.

## Project Collaborators

The project dashboard includes a `Collaborators` workspace for the primary
advisor, co-advisors, and administrators acting as supervisors.

### Role Matrix

| Capability | Primary advisor | Co-advisor | Reviewer | Observer | Student | Administrator |
|---|---:|---:|---:|---:|---:|---:|
| View project overview/tasks/permitted materials | Yes | Yes | Yes | Yes | Yes | Yes |
| Manage students | Yes | Yes | No | No | No | Yes |
| Add/remove co-advisor, reviewer, observer | Yes | No | No | No | No | Yes |
| Transfer primary ownership | Yes | No | No | No | No | Yes |
| Assign submission reviews | Yes | Yes | No | No | No | Yes |
| Review assigned target and comment | Yes | Yes | Assigned only | No | No | Yes |
| Mutate project work | Yes | Yes | No | No | Assigned tasks/reports only | Supervision only |
| Create/own project or hold membership | Yes | No | No | No | No | No |

- The collaborator panel uses a searchable teacher combobox for co-advisor,
  reviewer, observer, ownership transfer, and review assignment. Only active,
  verified, approved teachers appear.
- Current collaborators appear in a fixed-height role-grouped list. Each row
  shows role, eligibility state, assignment count, and only actions allowed to
  the current user.
- Reviewer assignment selects both a target and one or more eligible reviewers.
  Reviewer access is limited to the assigned report/writing version, its
  revision history, and connected inline comments.
- Observer views are read-only. Controls are omitted rather than merely
  disabled.

### Governance Hold

- A held project displays a persistent banner under project navigation with the
  hold reason and allowed non-destructive actions.
- Mutating controls affected by the hold are omitted or disabled with a
  localized reason.
- Administrators receive a transfer control in the banner. Resolving the hold
  requires selecting an eligible teacher and confirmation.
- Teachers and students can continue reads and non-destructive work explicitly
  permitted by the API capabilities response.

## Administrator Audit Console

### Route

`/admin/audit` is available only to administrators and appears in the
administrator operations navigation.

### Layout

- At widths of 900px and above, filters occupy a compact top band, the
  cursor-paginated event list occupies the left column, and event detail
  occupies the right column.
- Below 900px, the list is the primary view and event detail opens as a
  half-screen sheet. At 390px, controls wrap without horizontal page overflow.
- The event list has a stable height and internal scrolling. Selecting an event
  does not resize or replace the filter region.
- Filters cover time range, category, outcome, actor, project/target, action,
  and correlation ID. Applied filters are URL-backed and restorable.
- Detail shows actor snapshot, target snapshot, reason, correlation ID,
  redaction version, and structured metadata. Sensitive values are absent, not
  visually concealed client-side.
- Export uses the active filters, shows queued/processing/ready/failed/expired
  status, and exposes download only when the server capability allows it.

## Release Acceptance Experience

There is no production application screen for specification acceptance.
Repository maintainers use the version-controlled acceptance files and checker.
CI annotations and release logs must report:

- feature identifier and normative revision;
- Product, Testing, and Development decisions;
- stale, rejected, pending, or accepted disciplines;
- active exception identifier, scope, owner, approver, and expiry when used;
- a non-secret remediation command.

Changing non-normative formatting or review metadata must not stale a decision.
Changing a normative section must surface all prior decisions as stale.

## Accessibility and Responsive Acceptance

- All dialogs and sheets trap focus, return focus to their trigger, and close
  with Escape where dismissal is safe.
- Comboboxes expose labels, expanded state, selected values, empty results, and
  validation through ARIA semantics.
- Status is never conveyed by color alone. Toasts use the existing live region.
- Primary workflows are keyboard-complete at 390px, 900px, and 1440px with no
  clipped controls, visible-text overlap, or page-level horizontal scrolling.

