# Research: Research Group Operations

## Decision: Django REST backend with domain services

**Rationale**: Django provides mature authentication, authorization hooks,
transaction handling, admin support, and relational modeling for project-scoped
records. Django REST Framework gives a clear contract layer for the React
frontend while keeping project isolation checks centralized in backend
permissions and querysets.

**Alternatives considered**: A monolithic server-rendered Django app would reduce
frontend moving parts but would make rich inline comments, booking calendars, and
review queues less ergonomic. A lighter backend framework would require more
custom work for authentication, admin operations, and relational integrity.

## Decision: React with TypeScript and Vite for the web app

**Rationale**: The workflows require responsive task trees, version history,
inline review interactions, booking calendars, optimistic status feedback, and
project context cues. React with TypeScript supports strongly typed UI state and
contract-aware data access, while Vite keeps development and test feedback fast.

**Alternatives considered**: Server-rendered pages were considered for simpler
forms, but the inline commenting and booking interactions benefit from a richer
client experience. A larger frontend meta-framework was not needed for this
operations application.

## Decision: PostgreSQL as system of record

**Rationale**: The feature requires durable relationships across projects,
memberships, hierarchical tasks, versioned submissions, comments, bookings,
notifications, and audit events. PostgreSQL supports transactions and relational
constraints needed to keep all records project-scoped and booking-safe.

**Alternatives considered**: A document store would make version documents easy
to persist but would weaken relational constraints for project isolation,
membership authorization, and overlapping bookings.

## Decision: Redis plus Celery for email and reminder processing

**Rationale**: Email notifications and deadline reminders should not block user
actions. Redis provides a queue broker and short-lived locking/caching layer,
while Celery workers and a scheduler can process new submissions, pending
reviews, approaching deadlines, booking changes, and retryable delivery events.

**Alternatives considered**: Sending emails inline during requests would be
simpler but would risk slow submissions and inconsistent retries. A managed queue
can be revisited later but Docker Compose Redis is enough for the planned local
and initial deployment topology.

## Decision: Project isolation enforced in data model, querysets, permissions, and contracts

**Rationale**: The specification makes project grouping non-negotiable. Every
task, draft, report, comment, booking, notification, and audit event must carry
or derive a project identity. Backend access must filter by explicit project
membership by default, and contracts must require project-scoped routes for
research records.

**Alternatives considered**: Filtering project context only in the frontend was
rejected because it cannot protect data. Global record routes were rejected
because they increase the risk of cross-project lookup and authorization errors.

## Decision: Nested task hierarchy with same-project validation

**Rationale**: Hierarchical tasks need parent-child relationships, deadline
rules, and cycle prevention. Keeping hierarchy in one task entity with
same-project parent validation supports simple rendering and clear ownership
without introducing a separate planning structure.

**Alternatives considered**: A separate work-breakdown entity was rejected for
this phase because it duplicates task fields and adds unnecessary workflow
complexity.

## Decision: Versioned draft records with comments anchored to immutable versions

**Rationale**: Advisor comments must remain attached to the exact draft version
reviewed even after later submissions. Draft versions are therefore immutable
review targets, and comments reference a specific version plus an anchor.

**Alternatives considered**: Overwriting draft content in place was rejected
because it would break review history. Attaching comments only to a draft family
was rejected because comments could drift after new versions.

## Decision: Booking conflict prevention through transactional validation

**Rationale**: Equipment and seats cannot have overlapping reservations.
Conflict checks must occur when creating or changing bookings and be backed by
durable constraints or transaction-safe validation so concurrent requests cannot
double-book a resource.

**Alternatives considered**: Frontend-only availability checks were rejected
because they cannot prevent concurrent conflicts. Manual conflict resolution was
rejected because booking correctness is directly testable and expected by users.

## Decision: Docker Compose orchestration

**Rationale**: The user selected Docker Compose for deployment and
infrastructure orchestration. Compose can define the backend, frontend,
PostgreSQL, Redis, worker, scheduler, and email-capture service in a repeatable
environment for local validation and initial deployment.

**Alternatives considered**: Running services directly on the host was rejected
because it weakens reproducibility. Kubernetes was not chosen because the scope
does not require that operational complexity.
