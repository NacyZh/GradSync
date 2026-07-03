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

## Decision: Tailwind CSS plus shadcn/ui for production frontend architecture

**Rationale**: The frontend must be a production-grade operations interface.
Tailwind CSS provides explicit design tokens, responsive density controls, and
predictable utility composition in the existing Vite build. shadcn/ui provides
source-owned React components based on Radix UI primitives, which keeps
accessibility behavior, keyboard interaction, and component variants reviewable
inside the repository instead of hidden behind a binary design-system
dependency. This matches GradSync's need for a centered background login page,
dense role-aware dashboards, forms, review queues, booking controls,
notification surfaces, dialogs, menus, tabs, and table-like scanning interfaces.

**Alternatives considered**: Continuing ad hoc CSS was rejected because it
duplicates layout, focus, validation, and empty-state patterns. A full component
framework such as MUI or Ant Design was
rejected because it would impose a large visual and API surface that does not
match the existing Vite/TanStack Query code and would make domain-specific
workflow composition harder. Tailwind without shadcn/ui was rejected because it
would still require hand-rolling accessible dialogs, menus, tabs, popovers,
toasts, and form controls.

## Decision: Frontend module boundaries by workflow plus shared UI primitives

**Rationale**: Production workflows need clear ownership boundaries. Generated
or adapted shadcn/ui primitives live in `frontend/src/components/ui` and expose
low-level accessible controls. GradSync-specific adapters, empty/loading/error
states, confirmation flows, and feedback surfaces live in
`frontend/src/shared/ui`. User workflow composition remains in
`frontend/src/features/projects`, `tasks`, `submissions`, `resources`,
`notifications`, and future role workspaces. This keeps styling reusable without
moving domain behavior out of feature modules.

**Alternatives considered**: A single global component directory for all
frontend code was rejected because it blurs design primitives with project
workflow logic. Duplicating shadcn/ui components inside each feature was
rejected because variant drift would undermine visual consistency and
accessibility review.

## Decision: TanStack Query remains the server-state boundary

**Rationale**: Project, task, submission, booking, notification, and account
data are server-owned and already exposed through Django REST contracts.
TanStack Query handles request lifecycle, caching, invalidation, optimistic
feedback, and error states without adding a second API abstraction. Forms use
React Hook Form and Zod to provide client-side validation while preserving
backend validation as the source of truth.

**Alternatives considered**: Redux Toolkit and RTK Query were rejected for this
feature because the current data needs are server-state centric and do not yet
require a global client-state event model. Introducing them now would duplicate
TanStack Query responsibilities and increase migration cost without a clear
production benefit.

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

## Decision: Configurable email delivery with visible status records

**Rationale**: Email is a required notification channel, so delivery settings
must be environment-driven and safe for production and local validation. Django's
email backend configuration will support SMTP in deployed environments and an
email-capture backend for local validation. Celery tasks write notification
status transitions for pending, queued, sent, failed, and skipped outcomes, mask
secrets in logs, and re-check recipient project eligibility before send.

**Alternatives considered**: Relying only on in-app notifications was rejected
because email delivery is in scope. Hard-coding one SMTP provider was rejected
because it would leak provider assumptions into domain logic and complicate
local testing.

## Decision: Custom resource catalog with typed fields and booking policy

**Rationale**: Different specialties need different resource libraries, so a
fixed equipment/seat model is too narrow. Resource management uses a
`ResourceType` template with typed custom fields, eligibility rules, booking
policy, and availability metadata, plus `ResourceItem` records for actual
bookable assets. Booking conflict prevention operates on the resource item
identity regardless of its professional type.

**Alternatives considered**: Keeping only hard-coded equipment and seat enums was
rejected because it would require code changes for every new professional
resource category. Storing all resource data as unvalidated free-form JSON was
rejected because custom fields still need validation, search, and stable UI
rendering.

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

## Decision: Project-scoped paper team library from local folder/file import

**Rationale**: Papers need to be searchable, downloadable, and isolated by
project membership while behaving as a team public library. Import is initiated
from explicit browser local folder/file selection and staged on the backend. A
metadata-first model stores title, authors, venue, year, supplied DOI/external
identifiers, tags, local import source labels, uploader, checksum, and optional
file attachment references in PostgreSQL, while files use Django's storage
abstraction so local media or object storage can be selected per environment.
This keeps authorization and duplicate detection in domain services instead of
in the frontend or storage backend. No default automatic external search or DOI
lookup runs during import.

**Alternatives considered**: Treating papers as draft versions was rejected
because library papers are reference assets rather than student submissions with
review status. A dedicated external literature manager or automatic online
search integration was rejected for this feature because project isolation,
duplicate explanations, authorization, and audit events must be first-class
GradSync behavior and the requested flow is local import. Storing only files
without structured metadata was rejected because it cannot support reliable
search, deduplication, or citation lookup workflows.

## Decision: Explainable duplicate detection for paper import

**Rationale**: Duplicate prevention must be deterministic and user-facing.
Local folder/file imports compute and persist file checksums when a file is
present, normalize supplied DOI and external identifiers, and fall back to
normalized title, first author, and year matching when identifiers are absent.
Batch imports are staged before commit so users can see accepted records,
duplicate matches, and validation errors together.

**Alternatives considered**: Exact filename matching was rejected because
renamed PDFs would bypass it. Fully automated fuzzy matching was rejected as the
only gate because false positives could block legitimate papers without a clear
reason. Global deduplication across all projects was rejected because unrelated
projects may intentionally keep separate metadata, notes, or attachments.

## Decision: Project code artifacts as local folder/archive imports, not hosted Git replacement

**Rationale**: The requested code library needs local folder import, optional
archive import, descriptions, search, download, and project separation. Modeling
code as `CodeArtifact` plus immutable `CodeArtifactVersion` records supports
source folders or repository snapshots, version labels or commit references,
checksums, local import metadata, supersede/archive states, and download audit
events without introducing a full Git hosting system.

**Alternatives considered**: Embedding a hosted Git service or implementing
branch/diff/merge workflows was rejected because it would materially expand the
product into repository hosting and CI execution. Automatic repository discovery
or background searching was rejected because the requested workflow is explicit
local import into a team public library. Storing code as generic attachments was
rejected because code needs descriptions, version labels, commit/reference
metadata, and supersede behavior distinct from paper files.

## Decision: Download authorization and audit are enforced at request time

**Rationale**: Paper and code files may outlive membership changes, so download
URLs must be mediated by backend endpoints that re-check current project
membership, archived/read-only rules, and attachment status before issuing a
file response or short-lived storage URL. Every successful download writes an
audit event with actor, target, project, timestamp, and file/version metadata.

**Alternatives considered**: Public or long-lived direct file URLs were rejected
because they bypass project isolation after membership changes. Frontend-only
download hiding was rejected because it cannot protect the file endpoint.

## Decision: Application-owned Chinese/English locale catalogs with persisted user preference

**Rationale**: Language switching is required for the existing React/Vite
workspace without changing authorization or stored research content. A typed
message catalog in the frontend plus a persisted user locale preference on the
backend supports immediate Chinese and English label updates, validation
summaries, empty states, confirmations, navigation, and workflow feedback while
keeping server validation codes stable. Backend responses should expose
machine-readable error codes with localized frontend messages where possible,
and fallback to server messages when no catalog entry exists.

**Alternatives considered**: Browser-only language detection was rejected
because users need an explicit persistent choice across devices. A full page
reload on language change was rejected because users must keep the current
workflow, focus, selected project, and unsaved-form warning. Automatic
translation of user-generated research content was rejected because it would
alter scholarly records and introduce accuracy risk. Adding a heavy i18n
framework immediately was deferred unless typed local catalogs become
insufficient for pluralization, date/number formatting, or translation workflow.

## Decision: Booking conflict prevention through transactional validation

**Rationale**: Configured resource items cannot have overlapping reservations.
Conflict checks must occur when creating or changing bookings and be backed by
durable constraints or transaction-safe validation so concurrent requests cannot
double-book a resource item.

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
