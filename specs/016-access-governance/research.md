# Research: Access and Release Governance

## Decision 1: Add an authoritative account session registry

**Decision**: Create one account-session record at login and bind both the
Django browser session and every JWT refresh/access token to its opaque session
identifier. Preserve the session identifier across refresh rotation. Every
protected JWT request and refresh checks account status plus the session's
active/revoked/expired state. Session revocation blacklists known refresh tokens
and deletes the linked Django session where present, but the account-session
record is the authoritative denial state.

**Rationale**: GradSync currently supports both session authentication and JWT
authentication. The SimpleJWT blacklist can revoke individual refresh tokens
but does not represent the browser session or a stable device session across
rotation. A shared record makes session inventory and "revoke this device"
consistent and allows access tokens to be denied before their nominal expiry.

**Alternatives considered**:

- SimpleJWT blacklist only: rejected because it cannot list/correlate Django
  sessions and rotated refresh tokens as one device session.
- Django sessions only: rejected because Bearer access tokens would remain valid
  independently.
- Redis-only denylist: rejected because revocation correctness must survive
  cache loss and restore.
- Revoke by changing a user-wide token version only: useful for "revoke all"
  but cannot support individual device inventory/revocation.

## Decision 2: Force re-authentication for legacy unbound refresh sessions

**Decision**: Tokens issued before the session registry that lack a session
identifier may use their already-issued short-lived access token until expiry,
but refresh rotation rejects them and clears the refresh cookie. The user signs
in again to create a registered session. Existing Django sessions without an
account-session record are invalidated during rollout.

**Rationale**: Existing JWT and Django session records cannot be reliably paired
after the fact. Guessing associations would create misleading session inventory
and incomplete revocation. The current access token lifetime is short, so
bounded re-authentication is safer than an ambiguous migration.

**Alternatives considered**:

- Infer pairings by user and timestamps: rejected as unreliable when a user has
  multiple browsers.
- Permit legacy refresh until natural expiry: rejected because the session
  inventory would claim complete revocation while legacy refresh remained.
- Global logout at deployment: secure but unnecessarily interrupts active
  access tokens; bounded access expiry is sufficient.

## Decision 3: Use hashed single-use recovery and email-change secrets

**Decision**: Generate cryptographically random recovery tokens and numeric or
opaque email verification codes, store only keyed/non-recoverable hashes, bind
them to one account and purpose, supersede older pending requests, expire them
after 30 minutes, and consume them under a row lock. Public recovery requests
always return the same accepted response. Delivery records reference the
request without containing the secret.

**Rationale**: This follows the existing verification-code lifecycle while
removing its current plaintext-code compatibility field from new security
flows. Row locking and one-current-request constraints prevent concurrent
consumption/replay. Generic responses prevent account enumeration.

**Alternatives considered**:

- Signed self-contained reset links only: rejected because single-use,
  supersession, delivery state, and audit are harder to enforce centrally.
- Reuse registration verification rows: rejected because recovery, email
  change, and registration have different eligibility and invalidation rules.
- Store plaintext codes for support: rejected because operators do not need the
  secret and logs/backups would gain unnecessary exposure.

## Decision 4: Preserve account restriction state during recovery

**Decision**: Password recovery changes only the password credential and
revokes sessions. It does not alter `status`, `global_role`, `requested_role`,
`active_role`, email verification, or teacher approval. Pending-email accounts
use resend verification rather than recovery; verified pending-role accounts
may reset their password but remain unable to sign in until approved.

**Rationale**: Recovery proves control of an email channel, not eligibility for
an approved role or reactivation. Separating credential recovery from lifecycle
status prevents the exact bypass found in earlier account reactivation logic.

**Alternatives considered**:

- Reactivate suspended users after reset: rejected as privilege escalation.
- Block all non-active accounts from reset: rejected because a verified pending
  teacher still needs to maintain credential control while awaiting approval.

## Decision 5: Keep the current project advisor field as primary ownership

**Decision**: Retain `ResearchProject.advisor` as the canonical primary advisor
for backward compatibility. The matching active membership keeps role value
`advisor`; add `co_advisor` for collaborative managers. Enforce one active
primary-advisor membership per project and service-level equality with the
project advisor. Administrators are globally authorized supervisors and are not
eligible project owners or collaborator members.

**Rationale**: Renaming/removing the existing field and role would touch every
project, task, report, notification, material, test, and seed path. Keeping the
canonical field avoids a broad destructive migration while still exposing the
business term "Primary advisor" in contracts/UI.

**Alternatives considered**:

- New project-owner table replacing the advisor field: rejected as needless
  dual ownership and migration risk.
- Treat every advisor membership as equal owner: rejected because the
  clarification requires exactly one primary advisor.
- Allow administrator owners: rejected by the clarified global-supervision
  model and least-privilege boundary.

## Decision 6: Centralize project capabilities and use governance hold

**Decision**: Replace scattered advisor/reviewer checks with one project access
service returning explicit read/write capabilities for primary advisor,
co-advisor, reviewer, observer, student, and administrator. Add project
governance state `normal|hold`. Hold blocks membership, role, ownership,
archive, delete, and other destructive governance actions; existing authorized
reads and non-destructive project work continue. Only an administrator can
resolve hold by transferring ownership to an eligible teacher with a reason.

**Rationale**: Existing checks incorrectly treat reviewers as advisors in some
material paths and assume every administrator can also own/create projects.
One capability source keeps backend authorization and frontend controls aligned.
Hold avoids unsafe automatic promotion and avoids disrupting student work by
archiving the project.

**Alternatives considered**:

- Auto-promote a co-advisor: rejected because ownership is a governance decision.
- Auto-archive: rejected because it blocks ongoing student work.
- Let a co-advisor claim ownership: rejected because concurrent claims and
  accountability are unclear.

## Decision 7: Add target-specific reviewer assignments with explicit FKs

**Decision**: Add a review assignment record with exactly one target among
weekly progress report, writing version, or legacy draft version. Eligibility
requires active reviewer project membership and an active approved teacher
account. Existing writing participant records may seed candidate reviewers but
do not grant access to every version; authorized advisors assign each target.

**Rationale**: The clarified rule grants access only to assigned submissions.
Explicit nullable foreign keys plus a one-target check preserve referential
integrity across the bounded set of supported submission entities and avoid
unrestricted generic target IDs.

**Alternatives considered**:

- Project-level reviewer access to all submissions: rejected by clarification A.
- Content-type/generic foreign key: rejected because referential integrity and
  query/index behavior are weaker.
- Duplicate assignment tables per submission type: valid but needlessly repeats
  lifecycle, audit, and authorization behavior.

## Decision 8: Expand audit events additively and redact at write time

**Decision**: Add category, outcome, reason, correlation ID, actor snapshot, and
redaction version to existing audit events. Keep `event_type` as the stable
action key and existing snapshot JSON for backward compatibility. A central
sanitizer allowlists safe snapshot fields before persistence; serializers apply
defense-in-depth masking. Security/governance mutations create audit evidence
inside the same database transaction and roll back if audit persistence fails.

**Rationale**: Write-time minimization prevents secrets from entering database
backups, logs, detail views, and exports. Additive columns make filtering/indexing
predictable without rewriting historical rows. Atomic writes satisfy fail-closed
privileged operations.

**Alternatives considered**:

- Serializer-only redaction: rejected because secrets remain stored.
- Store full request payload encrypted: rejected because audit investigations
  do not need password/token/file bodies and key management adds risk.
- Separate external audit service: rejected as new operational infrastructure
  and a distributed-transaction failure mode.

## Decision 9: Use cursor pagination and asynchronous bounded CSV exports

**Decision**: Audit list uses stable newest-first cursor pagination over
`created_at,id`. Combined filters use indexed columns. Export creates an
`AuditExport` job with a normalized filter snapshot and high-water event ID,
then an existing Celery worker streams at most 10,000 rows to a short-lived CSV
file. Download re-checks administrator status, export ownership, readiness, and
expiry and uses existing secure download helpers.

**Rationale**: Cursor pagination avoids duplicates/skips when viewing audit
access creates new events. A high-water mark makes export deterministic while
new events arrive. CSV is portable for governance review and can be generated
with the standard library. Async streaming meets the 60-second requirement
without tying up a web request or loading all rows.

**Alternatives considered**:

- Synchronous JSON export: rejected for large response memory and timeout risk.
- Spreadsheet generation: rejected because it adds a dependency and executable
  document risks.
- Unbounded database dump: rejected by privacy and performance requirements.
- Redis job state: rejected because export evidence/status must survive broker
  restart.

## Decision 10: Keep audit evidence append-only for this feature

**Decision**: Do not implement automatic audit deletion. Enforce a minimum
365-day retention readiness policy and preserve all current rows. A future
institutional retention feature may archive/delete only after its own governed
specification. Audit export files expire and are deleted independently because
they are derived temporary artifacts.

**Rationale**: The spec requires at least 365 days but does not authorize
deletion after that point. Implementing retention deletion now could destroy
evidence and complicate rollback.

**Alternatives considered**:

- Delete exactly at 365 days: rejected because "at least" is a floor, not a
  deletion mandate.
- Archive to new object storage: rejected because no provider is in scope.

## Decision 11: Store specification acceptance in version-controlled JSON

**Decision**: Each governed feature uses `acceptance.json` conforming to
`contracts/acceptance.schema.json`. A repository policy file maps product,
testing, and development disciplines to allowed repository identities. A
standard-library checker extracts and canonicalizes normative specification
sections, computes a SHA-256 fingerprint, validates separate decisions,
reviewer authorization, stale status, and exception scope/expiry, and emits a
machine-readable and human-readable release report. The same account may sign
multiple disciplines as clarified.

**Rationale**: Release eligibility must be deterministically available before
deployment and cannot depend on production application/database availability.
JSON is reviewable, schema-validatable, diffable, and does not add a parser
dependency. Repository review/branch protection remains the authority for who
may merge policy and decision changes.

**Alternatives considered**:

- Store decisions in the production database: rejected because CI and rollback
  cannot reliably reproduce release eligibility.
- Infer acceptance from free-text `spec.md` statuses: rejected because revision
  binding and structured exception validation are unreliable.
- Use tags/commit messages only: rejected because three discipline decisions,
  rationale, staleness, and exceptions are difficult to query.
- Introduce a separate governance SaaS: rejected as external scope and cost.

## Decision 12: Fingerprint only deterministic normative sections

**Decision**: The checker fingerprints normalized content under user stories,
exception/boundary/degradation scenarios, quantifiable acceptance criteria,
dependencies/assumptions/scope, and requirements. Front matter, status,
clarification history, whitespace-only formatting, and explanatory overview
text do not affect the normative fingerprint. Heading identities and ordered
content are retained during canonicalization.

**Rationale**: This directly implements clarification A: normative changes make
decisions stale while metadata/formatting/explanatory edits do not. A
deterministic extractor prevents the author from manually declaring a change
non-material.

**Alternatives considered**:

- Hash the whole file: rejected because date/status/format edits cause needless
  re-approval.
- Let authors mark materiality: rejected because it can bypass the gate.
- Let one product reviewer decide: rejected because the release check would not
  be deterministic.

## Decision 13: Integrate acceptance checks before production image/deploy

**Decision**: CI validates all tracked feature acceptance records and schema
consistency as an ordinary test, but production release enforcement runs after
tests and before production image/deployment. A feature with pending/rejected/
stale reviews blocks release unless one active exception exactly covers the
feature revision and release scope. Exception owner and approver must differ;
maximum validity is 14 days.

**Rationale**: Pull requests need fast visibility into governance drift, while
production must fail closed. Running before deployment avoids contacting
production or building a knowingly unreleasable rollout.

**Alternatives considered**:

- Block every development test run while reviews are pending: rejected because
  implementation must be testable before final acceptance.
- Check only during deployment: rejected because feedback arrives too late.
- Permit environment-variable bypass: rejected because it is unaudited and
  unbounded.

## Decision 14: Reuse existing frontend patterns

**Decision**: Add public forgot/reset routes outside the authenticated layout;
place email/session controls in Profile; place collaborators in the project
dashboard; add an admin-only Audit navigation route. Use searchable dropdowns,
left-list/right-detail audit layout, global confirmation/toast feedback, TanStack
Query invalidation/live project events, runtime bilingual catalogs, bounded
scroll regions, and existing responsive/accessibility checks.

**Rationale**: These patterns already exist and have component/E2E coverage.
They minimize cross-feature imports and avoid duplicate notification or form
status mechanisms.

**Alternatives considered**:

- New security settings application: rejected as unnecessary navigation.
- Audit modal in account administration: rejected because search/filter/detail/
  export is a full workspace and would overload account controls.
- Form-local mutation messages: rejected by the existing global feedback rule.
