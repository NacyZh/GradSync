# Frontend UI Contract: Research Execution Loop

## Shared Interaction Rules

- New routes remain inside the existing authenticated shell and project
  context. Project-level navigation adds `Execution` beside Dashboard, Reviews,
  Reports, Materials, Writing, Resources, Papers, Documents, and Code.
- Every server capability controls whether a command is rendered. The frontend
  never infers write permission from account role alone and never exposes a
  disabled destructive control to a role that cannot perform it.
- Mutation completion, failure, conflict, retry, and unavailable feedback uses
  the existing global bottom-right toast. Forms retain only field-level
  validation beside the affected control.
- Potentially large collections use bounded list/detail layouts. Lists have
  stable height, internal scrolling, search/filter controls outside the scroll
  region, and selection that does not resize adjacent detail.
- Searchable member fields are input-driven comboboxes backed by eligible
  project members. They do not dump the whole account directory into the page.
- Status is conveyed by text/icon as well as color. Current status, permitted
  next actions, and historical transitions are visually separate.
- All new labels, empty/loading/error/conflict/stale states, validation
  messages, notifications, export headings, metric definitions, and screen
  reader text exist in English and Simplified Chinese.
- Existing project event polling invalidates the affected query keys. Last
  successful content remains visible in a stale state and valid form input is
  not reset by background refresh.

## Project Navigation and Routes

| Route | Primary content | Roles |
|---|---|---|
| `/projects/:projectId` | Existing dashboard plus execution health summary | All visible project roles; role-safe values |
| `/projects/:projectId/execution` | Milestones, deliverables, decisions, and risks | All project roles; capability-specific actions |
| `/projects/:projectId/reports` | Periods, report form/history, templates, analytics | Students submit own reports; advisors manage/review/analyze; assigned reviewers see assigned reports |
| `/projects/:projectId/reviews` | Existing report/writing queue plus assigned deliverable recommendation | Advisors and assigned reviewers |
| `/profile` | Existing profile plus notification preferences | Current account |
| `/admin/audit` | Existing audit console plus privacy-safe notification operations summary | Administrator only |

The project route bar is a horizontally scrollable navigation strip at narrow
widths. It does not wrap into multiple overlapping rows, and its scroll
position preserves the selected route.

## Role Matrix

| Capability | Primary advisor | Co-advisor | Reviewer | Observer | Student | Administrator |
|---|---:|---:|---:|---:|---:|---:|
| View general milestones/deliverables | Yes | Yes | Assigned/permitted context | Yes | Yes | Supervision |
| Create/edit/archive milestones | Yes | Yes | No | No | No | Explicit audited intervention only |
| Create/edit/archive deliverable plans | Yes | Yes | No | No | No | Explicit audited intervention only |
| Update assigned deliverable progress/evidence | Yes | Yes | No | No | Assigned only | No ordinary content edit |
| Submit deliverable revision | Yes | Yes | No | No | Assigned only | No |
| Recommend accept/return | Yes | Yes | Assigned only | No | No | No |
| Issue final deliverable decision | Yes | Yes | No | No | No | Explicit audited intervention only |
| Configure/publish report template | Yes | Yes | No | No | No | Read/operations only |
| Submit periodic report | No | No | No | No | Own report | No |
| View project/member analytics | Yes | Yes | Assigned report only, no aggregate | General project health only | Own trends | Aggregate supervision |
| Publish/supersede decisions | Yes | Yes | No | No | No | Explicit audited intervention only |
| Raise risks | Yes | Yes | Yes | No | Yes | Supervision only |
| Triage/close/reopen risks | Yes | Yes | No | No | No | Explicit audited intervention only |
| Change project reminder thresholds | Yes | No | No | No | No | Read/operations only |

Administrator intervention is never a hidden role shortcut. The action requires
the existing supervisor capability, confirmation, and a reason and produces an
audit event.

## Project Dashboard

- Replace task-only progress interpretation with a compact execution summary:
  milestone counts, accepted/required deliverables, pending reviews, missing
  reports, open/high risks, and unresolved required notifications.
- Existing Task Plan/Task Detail remains the daily-work surface. It does not
  duplicate milestone or deliverable detail.
- Summary items are links to the matching filtered Execution/Reports view.
- At desktop widths, summary metrics use a stable grid. At mobile widths, they
  become a two-column or single-column scan without horizontal page overflow.
- No recent-activity panel is reintroduced; event information belongs to
  notifications, history, and audit surfaces.

## Execution Workspace

### Layout

- The route uses tabs: `Milestones`, `Deliverables`, `Decisions`, and `Risks`.
- At widths of 900 CSS px and above, the selected tab uses a left list and
  right detail editor/viewer. The list occupies approximately 35-42% with a
  minimum usable width of 18rem; detail uses the remaining width.
- Below 900 px, the list is the primary screen. Selecting an item opens detail
  in a full-width view or accessible half-screen sheet with a visible Back
  action.
- List/filter region and detail region have a viewport-bounded height and
  independent vertical scrolling. A long rationale, evidence history, or link
  list never grows the whole page without bound.
- Create actions open a dialog or dedicated detail state. There are no
  persistent create forms beneath the lists.

### Milestones

- List rows show title, target date, owner summary, required acceptance count,
  and derived status only.
- Detail shows description, owners, ordered deliverables, date, derivation
  explanation, linked risks/decisions, and change history.
- Advisor create/edit uses member comboboxes, date input, and an order control.
  Status is never directly editable.
- Archive requires confirmation and a reason. Historical references remain
  available.

### Deliverables

- List filters include milestone, status, assignee, due range, and search.
- Detail shows acceptance criteria, assignees, linked tasks, progress, current
  state, evidence, reviewer recommendation, advisor decision, and revision
  history.
- Student-assignee controls are limited to progress, blocked reason, evidence,
  and submit. Planning fields are absent.
- Evidence selector groups existing project materials, tasks, and reports in
  searchable comboboxes and supports a validated HTTPS link. Selected evidence
  appears as removable rows before submission, not as an exposed full list.
- Reviewer recommendation presents `Recommend acceptance` and `Recommend
  return`; it explicitly states that advisor final acceptance is still
  required.
- Advisor final decision is a separate control after any required
  recommendation. Return requires rationale. Accept names the revision being
  accepted.
- Revision history is newest first, bounded, and reveals only linked evidence
  the current role can read. Unavailable evidence shows type and safe historical
  label without a broken deep link.

### Decisions

- List rows show title, effective date, owner, and current/superseded status.
- Detail shows context, options considered, selected outcome, rationale,
  affected work, publication actor/time, and predecessor/successor links.
- Published content has no edit/delete control. Advisors use `Supersede` to
  create a complete successor while viewing the old record for reference.
- Observers can read published decision content unless a linked target itself
  is protected. Reviewer access is limited to decision context attached to an
  assigned review target.

### Risks

- List filters include state, severity, owner, review date, and search.
- Rows show title, owner, fixed-matrix severity, review date, and state.
- Any eligible project member uses a compact `Raise risk` dialog with title,
  description, source, and optional links.
- Advisor triage uses two three-option segmented controls for Likelihood and
  Impact. The derived 3-by-3 result and explanation update immediately, but the
  server remains authoritative.
- Treatment, owner, and review date are required during triage.
- `Start mitigation`, `Accept`, `Resolve`, and `Reopen` are explicit commands,
  each showing required rationale/evidence and the resulting reminder behavior.
- Revision history displays actor, time, previous/new state, matrix inputs,
  severity, owner, review date, and reason.

## Reports Workspace

### Tabs and Role Views

- `Periods`: all roles see permitted period/report status; students enter their
  own current report from here.
- `History`: students see own revisions; advisors see project members; assigned
  reviewers see only assigned report targets.
- `Template`: visible to advisors; published history is read-only and one draft
  can be edited.
- `Analytics`: advisors see project/member filters; students see only their own
  traceable trends; administrators see supervision aggregates without private
  narrative responses.

### Template Editor

- Field palette contains Long text, Number, Percentage, Single choice, Multiple
  choice, Milestone/Deliverable progress, and Risk/Blocker.
- Fields are ordered through keyboard-capable up/down controls. Drag-only
  ordering is not permitted.
- Each field has bilingual label/help text, required toggle, and type-specific
  settings. Choice options require both locale labels.
- The editor has a fixed preview region showing the student form without
  nesting a card inside another card.
- Publishing requires confirmation that the version applies only to reporting
  periods opened later. The currently open period and drafts are named as
  unchanged.

### Report Form and Revisions

- The selected Reporting Period displays its locked template version and due
  time.
- Type-specific accessible controls validate before submission. Percentage uses
  a 0-100 numeric input; member-facing analytical fields display units.
- Execution progress selects authorized milestones/deliverables; risk/blocker
  entries can raise or link a risk through an explicit choice.
- Submit names the period and revision. A returned report reopens only through
  the existing revise/resubmit lifecycle.
- Historical revisions render with their own template version, response labels,
  review outcome, feedback, and source links.

### Analytics

- Date range is bounded to at most 104 weekly periods.
- Summary includes expected/on-time/late/missing and review outcome counts,
  milestone/deliverable state, blocker/risk trends, and configured quantitative
  series.
- Every visual shows metric definition, unit, population, date range, missing
  count, and source-report action. Missing values show `Unavailable`, never
  zero.
- Charts have an adjacent data-table representation and do not rely on color
  alone. No rank, productivity score, or implied performance label appears.
- Export uses the active filters and locale, reports completion through global
  toast, and downloads only server-authorized rows.

## Notification Center

### Trigger and Drawer

- The existing top-right bell remains the only global notification entry.
- Its red dot appears when unread notifications exist and clears only after the
  displayed notification IDs are confirmed read. Pending actions remain
  visible through a separate count/filter after reading.
- The existing dialog becomes a right-aligned half-screen drawer on desktop and
  a near-full-width sheet on mobile. It never covers the entire desktop
  workspace or creates page-level horizontal scroll.

### Filters and Items

- Header filters: `Unread`, `Pending action`, category, project, and time. A
  `Mark displayed as read` command affects only the loaded authorized IDs.
- Each item shows category icon, localized subject, project context when
  permitted, created/due time, delivery warning when relevant, and one outcome
  badge.
- Informational items open their authorized target.
- Acknowledgement-required items expose a clear `Acknowledge` command.
- Action-required items expose `Open action`; they become complete only after
  the authoritative business operation succeeds.
- Expired and unavailable items remain understandable but never reveal deleted
  or unauthorized target metadata.
- Loading more uses cursor pagination and preserves current scroll/selection.

### Preferences

- `/profile` includes a `Notifications` section with one quiet-hours toggle,
  start/end time, timezone, and email toggle per category.
- In-app delivery and mandatory security email are visibly fixed, not rendered
  as editable toggles.
- Only the Primary Advisor sees project reminder policy in project settings.
  Numeric controls display effective system default and permitted min/max.
- Quiet-hour and project-threshold updates use optimistic version handling.

## Administrator Operations

- `/admin/audit` gains a compact Notification Operations tab or band showing
  selected-period counts for pending/retrying/failed delivery, pending/expired/
  completed outcomes, and scheduler lag.
- No notification subject, report content, decision rationale, member email, or
  material label appears in aggregate operations.
- Project list supervision may expose execution-health counts and governance
  hold state, linking to role-safe project summary. Ordinary content edit
  controls remain absent.

## Live Refresh and Conflict Handling

- Project event types invalidate only related keys:
  `execution-summary`, `milestones`, `deliverables`, `decisions`, `risks`,
  `report-periods`, `reports`, `report-analytics`, and project notifications.
- Global notification polling remains independent and refreshes unread/pending
  counts every 15 seconds and on window focus.
- A `409` response keeps user input, displays a global conflict toast, and
  offers reload/compare. It never silently overwrites the current version.
- If access is removed, the next protected read/action clears private cached
  project data and returns to `/projects` without rendering stale metadata.
- If analytics or calendar projection fails, source records remain usable and
  the affected panel shows a bounded unavailable/retry state.

## Accessibility and Responsive Acceptance

- Tabs, sheets, dialogs, comboboxes, segmented controls, list selection,
  revision history, and charts are keyboard complete. Focus returns to the
  invoking control when a dismissible overlay closes.
- Lists expose selected state and item counts; status announcements use the
  existing live region without duplicating global toast content.
- Risk matrix controls have explicit group labels. Chart data is available as
  semantic tables. Required fields and errors are programmatically associated.
- At 390, 900, and 1440 CSS px, no visible primary text overlaps, no primary
  action is clipped, no project-level horizontal page scroll appears, and each
  fixed list/detail region remains operable at 200% zoom.
- Reduced-motion preferences disable nonessential transitions. Status and chart
  series remain distinguishable without color perception.
