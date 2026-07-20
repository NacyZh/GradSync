# Frontend UI Contract: Dashboard Calendar and Scheduling

## Dashboard Placement

The calendar is part of `/` and is visible to authenticated administrators,
teachers/advisors, and students. It does not add another primary navigation
destination and does not replace the top notification button.

Dashboard region order:

1. Existing role-specific dashboard heading
2. Calendar toolbar and role-aware schedule action
3. Calendar period view and upcoming agenda/detail workspace
4. Existing role-specific project and operations/work queues

Desktop/tablet layout:

- Calendar period view occupies the wider left column.
- The right column is fixed to the calendar workspace height and switches
  between upcoming agenda and selected-item detail; its list scrolls internally.
- Columns use `minmax(0, ...)` behavior so long titles cannot expand the page.

Mobile layout at 390 CSS px:

- Toolbar controls wrap into stable rows.
- Agenda is the default compact representation; month view remains available.
- Selected item detail opens after the agenda/calendar region rather than
  overlaying visible text.
- No calendar region, item label, action, dialog, or toast creates horizontal
  page overflow or visible text overlap.

## Calendar Toolbar

Required controls:

- Previous period icon button with tooltip
- Today action
- Next period icon button with tooltip
- Current period label
- Segmented view control: Month, Week, Day, Agenda
- Filter menu for Personal, Group, Project, Tasks, Reports, and Bookings
- `New schedule` action for every authenticated user
- Staff-only publish mode inside the schedule form, not a separate student-visible
  toolbar action
- Non-disruptive stale/updating indicator and manual refresh action when needed

Toolbar dimensions remain stable when labels, loading indicators, or counts
change. Previous/next controls use Lucide icons and programmatic names.

## Calendar Period Views

### Month

- Seven-column grid on supported tablet/desktop widths.
- Day cells have stable minimum dimensions and do not resize when an item loads.
- A bounded number of item rows is shown per cell; additional items use a
  `+N more` action that opens the day agenda.
- Today's date and the selected date are distinguishable without color alone.

### Week and Day

- Time labels and day columns use stable tracks.
- Overlapping occurrences are readable and selectable without text collision.
- All-day occurrences occupy a stable all-day row.
- The view scrolls inside its calendar region instead of expanding the page
  indefinitely.

### Agenda

- Chronological grouped list by local date.
- Cursor pagination or a bounded load-more action is used for longer periods.
- Each row shows time, title, scope/source, status, and organizer when relevant.
- Rows are buttons or links with a full programmatic item name and visible focus.

## Source and Status Presentation

Occurrences are differentiated by text/icon/badge as well as color:

- Personal: user-owned planning item
- Group: published by a teacher/advisor or administrator
- Project: project start/end milestone
- Task: assigned or staff-visible task deadline
- Report: configured future weekly deadline or authorized submitted report period
- Booking: requester/manager-visible resource booking

Cancelled and completed states use explicit text and accessible status labels.
System-derived items are visibly read-only and include an `Open source` action
only when the API returns an authorized `actionPath`.

The palette must remain restrained and must not make the dashboard a one-hue
surface. Source distinctions remain legible in light/dark themes and under
common color-vision differences.

## Item Selection and Detail

Selecting an item must not navigate away immediately. The right detail region
shows:

- Title and category/source
- Date/time or all-day range with timezone
- Description when authorized
- Organizer for group items
- Audience summary counts for group items; normal recipients do not receive a
  full account list unless their role permits it
- Recurrence and reminder summary for authored schedules
- Current status
- `Open source` for system-derived items
- Capability-driven Edit, Complete, Delete, Publish, Cancel, Revision history,
  and Delivery status actions

Private item details are rendered only from an owner-authorized detail response.
The UI must not infer administrator access from global role.

## Schedule Form Dialog

The create/edit form is a focused dialog or mobile sheet, not a permanent card
inside the dashboard. Required controls:

- Scope: Personal for all users; Group option only for teachers/advisors and
  administrators
- Category menu
- Title and description
- All-day toggle
- Start and end date/time controls
- Timezone display/selection
- Recurrence: None, Daily, Weekly, Monthly
- Recurrence interval and required end date
- Weekly weekday selection when applicable
- Up to three reminder offset selections
- Group audience controls when group scope is selected
- Primary Save or Publish command and Cancel command

Role behavior:

- Student: only Personal scope; no audience, publish, delivery, or group cancel
  controls.
- Teacher/advisor: Personal and Group; can edit/cancel own publications and view
  their delivery status.
- Administrator: Personal and Group; can edit/cancel any group publication and
  view delivery status, but cannot open other users' private item details.

Validation:

- Field guidance is attached to the relevant field for input correction.
- Operation outcomes are never rendered as form-local success/error banners.
- Save/publish/update/delete/cancel success or failure uses the existing global
  bottom-right toast.
- Invalid end ranges, recurrence bounds, reminder choices, empty audiences, and
  stale account/project selections preserve valid form input.

## Audience Selector

Group audience uses a mode selector plus dropdown search controls:

- Project multi-select dropdown, searching only projects visible and eligible to
  the publisher
- Account multi-select dropdown. For teachers/advisors it searches only active
  members of projects they can manage; for administrators it may search any
  active account using minimized identity fields.

There is no `All active members` or platform-wide account broadcast control.
At least one project or account must be selected.

Selected options appear as removable compact selections below the input. The
full candidate list is never permanently displayed. Search results are bounded,
keyboard navigable, and show enough identity context to distinguish accounts or
projects without exposing unrelated profile details. Duplicate selections are
disabled. A recipient-count preview and overlap deduplication note appear before
confirmation.

For recurring project audiences, recipient counts are a current preview. New
project members join future occurrences automatically and departed members lose
future visibility/reminders; historical occurrences and notifications remain
unchanged. The UI states this behavior before publication.

## Project Report Schedule

The project Reports view owns weekly report scheduling; the dashboard calendar
only renders the resulting read-only deadlines.

Staff controls in `/projects/:projectId/reports`:

- Enable/configure weekly report schedule
- Weekday menu
- Local deadline time input
- Timezone selector/display
- Save/update action
- Confirmed remove-schedule action

Role behavior:

- Project advisor/authorized teacher and administrator can configure one policy
  for an active project.
- Students and other members can view the configured deadline summary but cannot
  change it.
- Unconfigured projects show no assumed deadline; archived projects do not
  generate future deadlines.
- Save/remove operation outcomes use the global bottom-right toast. Stale-version
  conflicts retain valid form input and require current-state review.

## Recurrence Change and Destructive Actions

Editing or deleting/cancelling a recurring item requires a segmented scope
choice:

- This occurrence
- This and following occurrences
- Entire series

Private deletion and group cancellation require the existing confirmation
dialog pattern. Group items are cancelled rather than silently deleted.
Cancelled occurrences remain visible in the relevant historical/current period
until policy permits hiding them.

When `expectedVersion` is stale, the dialog remains open, displays a global
warning toast, and offers a clear action to load current details. It must not
automatically overwrite or discard form input.

## Conflict Warning

Overlap is advisory. Before final save/publish/update, visible conflicts are
shown in a compact confirmation dialog with time ranges and safe titles. The
user can return to editing or explicitly continue. Unauthorized schedule content
must never be exposed; a generic `Busy` label is used if a conflict can be
acknowledged without item-detail access. Resource booking hard-conflict behavior
remains in Resources and is not overridden here.

## Notifications and Live Refresh

- Publication, ordinary changes, audience removal, cancellation, and reminders
  appear once in the existing top notification popover.
- Publication and ordinary changes are in-app-only and do not send email.
- Cancellation and due reminders use both the in-app notification and existing
  email delivery. Delivery status distinguishes in-app creation from email
  queued/sent/failed/skipped outcomes.
- Selecting a schedule notification opens `/` with date/item query context or an
  authorized source route.
- Immediate operation results use only the existing global bottom-right toast.
- Calendar event polling invalidates affected period/detail/notification/
  delivery queries within five seconds in normal connected sessions.
- Background refresh retains the last successful calendar, current selected
  date/item, scroll position where practical, keyboard focus, open dropdowns,
  and valid in-progress form state.
- Refresh failure marks the view stale, retries automatically, and exposes a
  manual refresh control.

## Loading, Empty, and Error States

Required states:

- Loading initial calendar
- Updating period in background
- No schedule items in selected period
- Calendar temporarily unavailable with last-successful data retained
- No matching audience projects/accounts
- Selected audience became ineligible
- Invalid date/recurrence/reminder input
- Conflict confirmation required
- Stale version conflict
- Publication denied
- Reminder/delivery status delayed or partially failed
- Source record no longer available

Form validation remains associated with fields. Mutation feedback uses toast.
Page/data loading states use existing non-toast data-state patterns because they
describe persistent view state rather than an operation result.

## Accessibility and Responsive Contract

- Supported validation widths: 390, 900, and 1440 CSS px.
- All controls, day cells, occurrence rows, dialogs, selectors, and detail
  actions are keyboard operable with visible focus.
- Calendar grid uses an understandable grid/table semantic structure; agenda
  uses list semantics; selected/current/today states are announced.
- Source/status is not communicated by color alone.
- Live updates announce concise status without re-announcing the full calendar.
- Tooltips name unfamiliar icon-only controls.
- Text uses fixed responsive typography rather than viewport-width scaling and
  has zero letter spacing adjustments.
- Panels are not nested as decorative cards. Repeated agenda rows may use the
  existing compact list treatment rather than cards.
- Calendar/detail dimensions use stable min/max constraints so badges, loading
  states, long titles, and `+N more` controls cannot shift the primary layout.

## Client Module Boundary

`features/schedules/api.ts` owns public schedule/calendar API calls and exported
types. Calendar components may use `features/auth` public user context and
shared UI/query utilities. They must not import private APIs from projects,
tasks, submissions, resources, or notifications; source occurrences and action
paths come from the calendar API contract. `HomePage` composes the public
calendar workspace without owning schedule business logic.
