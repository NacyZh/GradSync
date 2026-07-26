# Research: Research Execution Loop

## Decision 1: Extend existing domain applications

**Decision**: Keep milestones, deliverables, decisions, and risks in
`apps.projects`; report templates, periods, responses, and analysis in
`apps.submissions`; notification policy and outcomes in `apps.notifications`;
and date projection in `apps.schedules`.

**Rationale**: These applications already own project capability checks,
weekly report revision behavior, email/in-app delivery, Celery scheduling,
calendar aggregation, audit events, and frontend feature routes. Extending them
keeps authorization next to the authoritative data and respects the repository
import-boundary test.

**Alternatives considered**:

- Create a new execution/workflow application: rejected because it would
  duplicate project authorization and become a cross-domain data owner.
- Put all records in Projects: rejected because report revisions and
  notification delivery already have mature independent lifecycles.
- Implement orchestration in the frontend: rejected because status derivation,
  privacy, retries, and audit must be server-authoritative.

## Decision 2: Use relational execution records with bounded JSON leaves

**Decision**: Model milestones, deliverables, assignees, revisions, evidence,
recommendations, decisions, risks, and report fields as explicit relational
records. Use JSON only for a bounded list of choice options, choice response
values, and safe immutable snapshots, all validated against a known field type.

**Rationale**: Project isolation, one-current-state constraints, accepted
revision history, due-date scans, filtering, and joins need referential
integrity and indexes. Fully normalized choice option tables add little value,
while unconstrained JSON documents weaken validation and analytics.

**Alternatives considered**:

- One JSON document per project execution plan: rejected because concurrent
  edits, indexes, role-scoped records, and partial history become fragile.
- One generic entity/attribute/value table: rejected because field validity and
  query behavior become difficult to reason about.
- A separate table for every report response type: rejected because it creates
  sparse parallel schemas and complex revision reads.

## Decision 3: Preserve audit-event polling for live refresh

**Decision**: Every committed execution mutation records a project audit event.
The existing project event feed and five-second `useProjectLiveRefresh` polling
invalidate only the affected TanStack Query keys.

**Rationale**: The current behavior already satisfies the five-second
convergence requirement and has stale-data degradation. Extending its event
types has lower operational cost than introducing a persistent connection
service. Audit events are committed with domain changes, so they are also a
reliable invalidation cursor.

**Alternatives considered**:

- WebSockets or Server-Sent Events: rejected because they add proxy,
  connection, authorization, retry, and deployment work without a tighter
  business target.
- Refresh the full dashboard after every timer: rejected because it discards
  list/detail state and causes avoidable traffic.
- Client-only optimistic truth: rejected because another actor may change
  acceptance, access, or risk state.

## Decision 4: Separate deliverable planning, submission, review, and acceptance

**Decision**: A deliverable owns mutable planning fields and a version.
Submission creates an immutable numbered revision with evidence snapshots. An
assigned reviewer may add one current accept-or-return recommendation per
revision. A primary advisor or co-advisor creates the final accepted/returned
decision; only an accepted advisor decision contributes to milestone
completion.

**Rationale**: This directly implements the clarification and prevents a task
completion or reviewer opinion from silently completing a milestone. Immutable
revisions preserve evidence when materials or assignments later change.

**Alternatives considered**:

- Store only the current deliverable status: rejected because return/resubmit
  history and accepted evidence would be lost.
- Let reviewers set final status: rejected by the clarified accountability
  boundary.
- Copy deliverables into Tasks: rejected because task completion is activity,
  not output acceptance.

## Decision 5: Derive milestone status transactionally

**Decision**: Store milestone lifecycle fields and a materialized current
status for indexed lists, but derive that status through one service from
required deliverable decisions, target date, open high risks, and archive
state. Recompute after every relevant committed event and during reconciliation.

**Rationale**: Query-time derivation across every deliverable and risk would
make lists expensive, while user-editable status would violate the
specification. A service-owned materialized status provides predictable reads
and can be checked against source records.

**Alternatives considered**:

- Compute every status in the browser: rejected because clients could disagree
  and hidden records would distort results.
- Let advisors mark milestones complete: rejected because required
  deliverables must control completion.
- Use database triggers: rejected because business rules and audit behavior
  would be split outside existing service conventions.

## Decision 6: Lock a report template at reporting-period opening

**Decision**: A logical project template has immutable numbered versions.
Advisors edit only a draft version, and publication makes it active for future
periods. The existing weekly report schedule opens a `ReportingPeriod` with the
then-active template version. Every draft and revision for that period uses the
locked version.

**Rationale**: Period locking gives all students in the same project/week an
identical structure and makes aggregates comparable. It also avoids trying to
migrate partially completed answers after publication.

**Alternatives considered**:

- Lock on first open/save per student: rejected because one period could contain
  different templates.
- Lock on submission: rejected because in-progress answers could become
  invalid without user action.
- Mutate the current template in place: rejected because historical reports
  would no longer be interpretable.

## Decision 7: Use controlled report fields and normalized response rows

**Decision**: Support `long_text`, `number`, `percentage`, `single_choice`,
`multiple_choice`, `execution_progress`, and `risk_blocker` fields. Template
field rows define order, requirement, unit, options, and source rules. Report
response rows store a validated value plus a numeric projection only when the
field is quantitative.

**Rationale**: Controlled fields cover the clarified use cases while allowing
server-side validation, accessible form controls, and source-traceable
analytics. Numeric projection avoids unsafe casts over heterogeneous values.

**Alternatives considered**:

- Arbitrary formulas or scripts: rejected by scope and because they create code
  execution, versioning, and support risks.
- Fixed sections only: rejected because projects need different measurable
  indicators.
- Store every answer in one JSON response: rejected because field-level
  validation, source links, and range aggregates become less reliable.

## Decision 8: Compute transparent analytics from source data

**Decision**: Calculate submission timeliness, review outcomes, accepted
deliverables, milestone state, declared blockers, and configured numeric field
series in PostgreSQL for a bounded project/date range. Cache the authorized
aggregate for at most 60 seconds in existing Redis using project event/version,
template version, locale-independent metric key, and range as the key. Return
source IDs, units, population, and missing-data treatment.

**Rationale**: The scale is modest and relational aggregation remains
explainable. Short caching protects repeated dashboard reads without making
Redis authoritative. Missing values remain null and do not become zero.

**Alternatives considered**:

- New analytics database/service: rejected as disproportionate infrastructure.
- Persist opaque composite scores: rejected by the no-ranking requirement.
- Calculate only in the browser: rejected because exports and users could
  produce inconsistent populations.

## Decision 9: Make decisions immutable and risks versioned

**Decision**: Publishing creates an immutable decision record. A changed
decision creates a successor that references the superseded record. Risks use
`raised`, `open`, `mitigating`, `accepted`, `resolved`, and reopened-to-`open`
transitions, each with an immutable revision containing prior/current values,
actor, rationale, and source. Likelihood and impact are low/medium/high and one
fixed 3-by-3 matrix derives low/medium/high severity.

**Rationale**: Decisions need durable rationale, while risks legitimately
change owner, treatment, dates, and state. The fixed matrix allows comparable
trends without false numerical precision.

**Alternatives considered**:

- Edit decisions in place: rejected because handover could not recover the
  original rationale.
- One append-only event stream for all project state: rejected because current
  list queries and migrations would become unnecessarily complex.
- Per-project risk formulas: rejected by clarification and cross-period
  comparability.

## Decision 10: Use explicit bounded links with safe snapshots

**Decision**: Execution links support only known target kinds: milestone,
deliverable, task, project material, weekly report, decision, and risk. The
service verifies project equality and target visibility at write/read time.
Links retain target kind, identifier, and a minimized title snapshot when a
linked target is later removed; the snapshot never restores protected content.

**Rationale**: The feature requires cross-record context and durable history,
but unrestricted generic links would allow project escape and weak referential
integrity. A bounded link service centralizes validation and redaction.

**Alternatives considered**:

- Store arbitrary URLs only: rejected because internal authorization cannot be
  enforced.
- Hard-delete links with targets: rejected because accepted evidence and
  decision rationale would become incomplete.
- Copy full linked records: rejected because it creates privacy and staleness
  problems.

## Decision 11: Separate notification delivery and business outcome

**Decision**: Extend each recipient notification with category, requirement
type, due/expiry, dedupe key, acknowledgement/action timestamps, and current
business outcome. Keep read receipts independent. Store each email/in-app
delivery attempt separately. A registry of server-side domain resolvers marks
action completion from committed target events; the client cannot arbitrarily
complete an action-required notification.

**Rationale**: Delivery, viewing, acknowledgement, and task completion answer
different questions. Domain reconciliation prevents a forged completion call
and automatically closes the notification when the actual deliverable review,
report submission, risk triage, or decision acknowledgement occurs.

**Alternatives considered**:

- Reuse delivery `status` for all states: rejected because `sent` cannot mean
  read or acted upon.
- Add a generic client `complete` endpoint: rejected because it would allow
  completion without the business action.
- Derive every outcome at read time: rejected because overdue/escalation scans
  and historical completion evidence need durable state.

## Decision 12: Use system defaults plus bounded project notification policy

**Decision**: System settings provide reminder lead, escalation delay, and
repeat limits. A primary advisor may override project values inside configured
minimum/maximum bounds using optimistic concurrency. User preferences control
email by category and quiet hours; they never disable in-app records, mandatory
security delivery, or required project escalation.

**Rationale**: This implements the clarification while preventing unbounded
notification fan-out. Project policy controls accountability; user policy
controls channel experience.

**Alternatives considered**:

- Fixed global values only: rejected because research projects have different
  cadences.
- Administrator-only configuration: rejected because it creates operational
  bottlenecks.
- Recipient-owned escalation: rejected because a recipient could suppress an
  accountability requirement.

## Decision 13: Reuse Celery/Beat with idempotent database claims

**Decision**: Extend the existing five-minute notification schedule with
bounded tasks for report-period opening, approaching-date reminders, overdue
escalation, action reconciliation, delivery retry, and derived-state
reconciliation. Jobs select indexed eligible rows in chunks, claim work with
row locks/skip-locked behavior, and use stable idempotency/dedupe keys.

**Rationale**: Worker, scheduler, Redis broker, readiness checks, and retry
patterns already exist. Database claims survive broker restart and prevent two
workers from producing duplicate active reminders.

**Alternatives considered**:

- Add another queue/scheduler: rejected as needless operations complexity.
- Execute fan-out synchronously in user requests: rejected because project
  member counts and email latency would affect interactive writes.
- Store job truth only in Redis: rejected because retry evidence and outcomes
  must survive cache/broker loss.

## Decision 14: Project dates remain calendar projections

**Decision**: Extend `schedules.projection_services` to expose read-only
milestone targets, deliverable due dates, risk review dates, and reporting
period deadlines. Source services remain authoritative; projection changes
appear through the existing calendar event cursor and no duplicate
`ScheduleItem` is created.

**Rationale**: Existing tasks, reports, projects, and bookings already use
read-only adapters. Reusing that pattern avoids synchronization rows and makes a
date edit immediately authoritative.

**Alternatives considered**:

- Create a mutable schedule item for each source date: rejected because two
  records could diverge and cancellation semantics would be ambiguous.
- Omit calendar integration: rejected by the specification.
- Move due-date ownership to Schedules: rejected because execution validation
  belongs to the source domain.

## Decision 15: Additive migration with legacy weekly-report compatibility

**Decision**: Create new tables/columns first. For every project with legacy
reports, create a default published template and period per historical
`report_week_start`, then attach reports and convert completed work, blockers,
and next steps to controlled responses in chunks. Keep legacy columns and
serializer aliases until a later governed removal. Existing notifications
default to informational with no fabricated acknowledgement/completion.

**Rationale**: Old report routes and deployed frontend versions must continue
to work during rolling deployment and rollback. Historical data must not imply
an acceptance or outcome that never occurred.

**Alternatives considered**:

- Replace the report table in one migration: rejected because it increases lock
  time and rollback risk.
- Treat all old notifications as acknowledged: rejected because that invents
  evidence.
- Skip historical template association: rejected because old reports could not
  render consistently in the new revision history.

## Security, Performance, and Operational Findings

- Authorization must be checked on both the source and target of every link and
  again when a stale deep link is followed.
- Reviewer recommendation endpoints require an active target-specific
  assignment; final decisions require active primary/co-advisor capability.
- Project delete/archive behavior must explicitly cover new records. Ordinary
  archive makes them read-only; confirmed project deletion follows existing
  cascading project policy while audit target snapshots remain minimized.
- Search, analytics, exports, and event feeds require explicit page/range/row
  limits. No endpoint returns a full account, notification, risk, or execution
  collection.
- Indexes must cover project/status/order/due fields, period/student/revision,
  recipient/outcome/due, delivery retry, and risk severity/review date.
- Rich text is not needed. Narrative values remain plain text; external
  evidence URLs allow only approved `https` links and are opened with safe
  browser isolation.
- Metrics expose counts, lag, and outcomes, never subjects, response bodies,
  rationale, material names, or user email.
- Backup/restore validation must include new relational history before enabling
  jobs; application rollback leaves additive schema and history intact.
