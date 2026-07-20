# Research: Dashboard Calendar and Scheduling

## Decision: Create a dedicated `schedules` domain

**Rationale**: Private ownership, group publication, recurrence, audience
resolution, occurrence exceptions, optimistic concurrency, and reminder
idempotency form one business boundary. Projects, tasks, reports, resources,
notifications, and audit remain authoritative for their own records; the new
domain aggregates authorized calendar projections without moving those records.

**Alternatives considered**:

- Add calendar fields and endpoints to Projects: rejected because personal and
  group-wide schedules are not necessarily project-scoped.
- Put schedule records in Notifications: rejected because a notification is a
  delivery record, not the source of schedule truth.
- Put all logic in the dashboard/frontend: rejected because privacy, recurrence,
  audience resolution, and reminder correctness require server authorization.

## Decision: Expand recurrence on the server with `python-dateutil`

**Rationale**: The server must be authoritative for timezone-aware daily,
weekly, and monthly rules so calendar queries and reminders use identical
occurrences. `python-dateutil` provides mature RFC-style recurrence behavior and
timezone-safe date arithmetic. Rules remain product-bounded: end date required,
maximum two-year horizon, maximum 1,000 generated occurrences, and a maximum
62-day calendar query window.

**Alternatives considered**:

- Hand-roll recurrence arithmetic: rejected because month-end, timezone, and
  exception behavior is deceptively error-prone.
- Persist every future occurrence: rejected because edits and audience changes
  create write amplification and stale rows.
- Support unrestricted RRULE strings: rejected because arbitrary combinations
  make validation, UX, performance, and support costs unbounded.

## Decision: Use `date-fns` for frontend date operations, not a calendar suite

**Rationale**: The frontend needs reliable period boundaries, calendar-grid
dates, comparisons, and locale-aware labels, while occurrence truth remains on
the server. `date-fns` is modular and tree-shakeable. Existing Radix controls,
Tailwind, and Lucide icons can produce a dashboard-specific accessible calendar
without adopting another visual system.

**Alternatives considered**:

- Native `Date` arithmetic only: rejected because period and locale edge cases
  would be duplicated across components.
- FullCalendar: rejected because its broad interaction/plugin surface, CSS, and
  bundle are unnecessary for the bounded dashboard experience.
- React Big Calendar: rejected because it still requires date adapters and
  imposes layout/interaction patterns that do not match the compact dashboard
  and mobile agenda contract.

## Decision: Store series rules and sparse occurrence exceptions

**Rationale**: A schedule item stores the recurrence rule; only edited,
completed, or cancelled occurrences create exception rows. Period queries
expand series only inside the requested window and merge exceptions. This keeps
storage proportional to actual edits and makes occurrence/future/series changes
explicit.

**Alternatives considered**:

- One row per generated occurrence: rejected because long series multiply rows
  and make series edits transactional and expensive.
- Store recurrence and exceptions in one JSON document: rejected because
  concurrency, indexing, audit, and targeted occurrence updates become weaker.

## Decision: Use project/account audiences and temporal recipient grants

**Rationale**: Publication writes deduplicated temporal `ScheduleRecipientGrant`
rows so visibility and delivery are explicit for each membership interval.
Audience source rows retain selected-project and selected-account intent; there
is no platform-wide all-account source. Before future occurrences/reminders and
after relevant membership/account changes, the resolver closes departed-member
grants and opens grants for new project members. Historical grants remain
immutable. Selected-account audiences remain explicit and are removed from
future delivery only when the selected account becomes ineligible.

**Alternatives considered**:

- Resolve audience only at read time: rejected because delivery deduplication,
  removal notices, and delivery status become expensive and ambiguous.
- Freeze all recipients forever at first publication: rejected because project
  membership and account status changes must affect future visibility/reminders.
- Mutate one current recipient row in place: rejected because remove/rejoin
  cycles would lose historical occurrence visibility evidence.
- Add an all-active account scope: rejected by clarification because it creates
  accidental platform-wide broadcast and account-directory exposure risk.
- Copy email addresses into schedule data: rejected because account identity and
  delivery addressing already have authoritative ownership.

## Decision: Bound direct-account search by publisher authority

**Rationale**: Advisors may search/select only active members of projects they
can manage. Administrators may search any active account with minimized identity
fields. Submitted IDs are revalidated against the same rule in the publication
transaction, so hidden UI is not an authorization boundary.

**Alternatives considered**:

- Let every staff user search all active accounts: rejected because it exposes a
  platform directory beyond a teacher's research scope.
- Let advisors search all students only: rejected because cross-project student
  visibility remains broader than the clarified boundary and excludes legitimate
  reviewer/advisor project members.
- Remove direct-account selection: rejected because publishers need subsets of
  a selected project's members.

## Decision: Aggregate system-derived items through read-only adapters

**Rationale**: A calendar aggregation service applies each source module's
visibility rules and maps project starts/ends, task deadlines, configured future
weekly report deadlines, submitted report periods, and booking windows into one
occurrence contract. Each projection includes a source type/id and authorized
action path and is never editable through schedule mutation endpoints.

**Alternatives considered**:

- Copy source dates into schedule tables: rejected because source changes would
  create synchronization drift.
- Use generic foreign keys for every projection: rejected because projections
  do not need persistence and generic relations weaken ownership/constraints.
- Let the frontend call and merge every feature API: rejected because that
  duplicates authorization and increases network/failure surfaces.

## Decision: Store one optional weekly report schedule per project

**Rationale**: Reports are periodic but different projects use different
deadlines. A submissions-owned one-to-one policy stores weekday, local deadline
time, timezone, version, and updater. Only an authorized advisor/administrator
may configure it for an active project. The calendar derives future report
deadlines for current members; absent or archived-project policies generate no
new future occurrences.

**Alternatives considered**:

- Use one workspace-wide weekday/time: rejected because it imposes one cadence
  on unrelated projects.
- Infer deadlines from submitted reports: rejected because past submission dates
  are not a reliable planning policy.
- Require manual group schedule publication for every report: rejected because
  it duplicates a stable periodic business rule and increases missed updates.

## Decision: Reuse notification delivery and Celery Beat

**Rationale**: The platform already records notifications, retries email
delivery, and runs reminder generation every five minutes. Add schedule event
types, an explicit delivery policy (`in_app` or `in_app_email`), and one
idempotent generator task to the existing notifications queue. Publication and
ordinary-change records are immediately visible in-app and are never selected
for email delivery. Cancellation and reminder records are visible in-app and
use existing email retry. `ScheduleNotificationDispatch` provides a unique
occurrence/recipient/event/offset/channel key before delivery is recorded,
preventing duplicates across task retries.

**Alternatives considered**:

- Add another scheduler or queue: rejected because it duplicates operations and
  is unnecessary for the five-minute service target.
- Browser-only reminders: rejected because users may be offline and reminders
  must appear in the central notification history.
- Email every event: rejected by clarification because publication and ordinary
  change mail would create avoidable notification fatigue.
- In-app only for cancellation/reminders: rejected because these time-sensitive
  events need an off-platform channel.
- Reuse notification target IDs without a dispatch record: rejected because the
  current notification table has no database uniqueness guarantee for this
  multi-dimensional idempotency key.

## Decision: Use version-based optimistic concurrency

**Rationale**: Every mutable schedule item has an integer version. Mutation
requests include `expectedVersion`; the service locks the row, compares the
version, applies the transaction, and increments it. A stale request returns
the current safe representation with a conflict response so the user reviews
newer data before retrying.

**Alternatives considered**:

- Last write wins: rejected because it can silently erase audience or timing
  changes.
- Distributed locks: rejected because database transactions are sufficient and
  avoid new infrastructure.
- Long-lived edit leases: rejected because they are operationally fragile and
  unnecessary for short form interactions.

## Decision: Use bounded event-version polling for live convergence

**Rationale**: TanStack Query and the project module already use mutation
invalidation and bounded event polling. A visibility-filtered schedule event
cursor every five seconds can invalidate calendar, detail, notification, and
delivery queries while retaining last-successful content and form state. This
meets the stated freshness target in the current deployment topology.

**Alternatives considered**:

- WebSockets or SSE: rejected because they add proxy, connection, monitoring,
  and degradation complexity without a stricter latency requirement.
- Refetch the entire calendar every five seconds: rejected because event cursors
  avoid unnecessary source aggregation work.
- Manual refresh only: rejected because connected views must converge after
  publication and changes.

## Decision: Do not introduce shared calendar-result caching initially

**Rationale**: Period results combine private data, dynamic membership, and
several source modules. Correct invalidation would be more complex than the
bounded indexed reads at the target scale. Request-local deduplication and
select/prefetch/batched source queries provide a safer baseline; performance
tests gate any later cache decision.

**Alternatives considered**:

- Cache per-user period results in Redis: deferred because invalidation must
  cover schedules, audiences, memberships, tasks, projects, reports, bookings,
  and account status.
- Cache shared group results only: deferred because personalized source
  projections still require merging and authorization.

## Security and Privacy Risk Assessment

- Private items require owner filters before object lookup so administrators
  cannot infer titles, descriptions, recurrence, or reminders from detail,
  conflict, event, audit, or delivery endpoints.
- Group controls hidden in the frontend are convenience only; all publish,
  audience, edit, cancel, and delivery-status requests repeat server role and
  ownership checks.
- Advisor audience search returns bounded active members of manageable projects;
  administrator search returns bounded active accounts. Both expose minimized
  identity fields, and raw IDs are revalidated at publication time.
- No endpoint or audience shape provides platform-wide all-account broadcast.
- System projection action paths are emitted only when the same request user can
  open the source record.
- Audit payloads record IDs, actor, scope counts, outcome, and timestamps for
  group actions but omit private titles/descriptions and personal reminder data.
- Text content is serialized as data and rendered with normal React escaping;
  no rich HTML is accepted.

## Performance and Operations Risk Assessment

- Calendar windows are capped at 62 days; agenda is cursor-paginated; recurrence
  generation has per-series and per-response caps.
- Composite indexes cover owner/scope/status/time, recipient/user validity
  intervals, project/account audience references, project report policies,
  exceptions, reminders, revisions, and per-channel dispatch idempotency.
- Source adapters batch by visible project/user and time range and avoid per-row
  queries.
- Audience publication is capped at 500 recipients and executes in bounded bulk
  inserts/updates inside one transaction.
- Reminder processing locks/claims bounded batches, skips no-longer-authorized
  recipients, sends only `in_app_email` events through email, and records
  channel-specific lag/retry outcomes without blocking API traffic.
- Schema-first deployment and application-first rollback avoid old-code access
  to missing tables. New tables are retained on rollback unless an explicit
  backup-backed destructive reversal is approved.
