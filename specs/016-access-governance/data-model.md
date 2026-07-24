# Data Model: Access and Release Governance

## Conventions

- Database timestamps are timezone-aware UTC.
- Security/governance mutations use row locks and atomic transactions.
- Public identifiers for recovery, sessions, and exports are opaque UUIDs; raw
  database IDs and secret material are not exposed.
- Secret values are generated once, delivered, and discarded. Persistence uses
  keyed/non-recoverable hashes only.
- Existing camelCase API fields map to snake_case persistence fields.
- Existing records and route contracts remain backward compatible unless the
  specification explicitly changes policy.

## 1. AccountRecoveryRequest

Represents one password-recovery lifecycle without revealing or storing the raw
recovery secret.

### Fields

| Field | Type | Rules |
|---|---|---|
| id | UUID | Primary/public identifier |
| user | FK User | Required, protected from deletion while request retained |
| token_hash | fixed string | Required, unique, non-recoverable |
| status | enum | `pending`, `consumed`, `superseded`, `expired`, `revoked` |
| requested_email_snapshot | email | Normalized address used for delivery/audit |
| requested_ip_hash | fixed string | Optional keyed hash; never raw IP in UI/export |
| requested_user_agent | string | Bounded, sanitized recognition context |
| expires_at | datetime | Required; default issuance + 30 minutes |
| consumed_at | datetime | Nullable; set once |
| superseded_at | datetime | Nullable |
| revoked_at | datetime | Nullable |
| delivery_notification | nullable FK Notification | Delivery status; no secret body |
| created_at | datetime | Required |
| updated_at | datetime | Required |

### Constraints and Indexes

- At most one `pending` request per user.
- `token_hash` is unique.
- Index `(user, status, created_at desc)`.
- Index `(status, expires_at)` for expiry/cleanup.
- Terminal status timestamps must match their state.

### State Transitions

```text
pending -> consumed
pending -> superseded
pending -> expired
pending -> revoked
terminal -> no transition
```

Creating a newer request locks the user/current pending request and changes the
old request to `superseded`. Successful consumption changes the password,
marks the request consumed, revokes all account sessions, and invalidates every
other pending recovery request in one transaction.

## 2. EmailChangeRequest

Represents a verified transition from the current sign-in email to a new unique
address.

### Fields

| Field | Type | Rules |
|---|---|---|
| id | UUID | Primary/public identifier |
| user | FK User | Required |
| previous_email | email | Immutable normalized snapshot |
| new_email | email | Normalized candidate |
| verification_hash | fixed string | Required, unique, non-recoverable |
| status | enum | `pending`, `verified`, `cancelled`, `superseded`, `expired` |
| expires_at | datetime | Required; default issuance + 30 minutes |
| verified_at | datetime | Nullable |
| cancelled_at | datetime | Nullable |
| delivery_notification | nullable FK Notification | New-address verification delivery |
| security_notification | nullable FK Notification | Old-address security notice |
| created_at | datetime | Required |
| updated_at | datetime | Required |

### Constraints and Indexes

- At most one `pending` email change per user.
- At most one pending request per normalized `new_email`.
- `verification_hash` is unique.
- `new_email` cannot equal `previous_email`.
- Index `(user, status, created_at desc)` and `(new_email, status)`.
- Completion locks both request and user, re-checks uniqueness, updates
  `User.email`, marks verified, revokes all other sessions, and preserves the
  current session only after issuing it fresh credentials bound to the new
  identity.

### State Transitions

```text
pending -> verified
pending -> cancelled
pending -> superseded
pending -> expired
terminal -> no transition
```

## 3. AccountSession

Authoritative session inventory shared by Django session authentication and JWT
authentication.

### Fields

| Field | Type | Rules |
|---|---|---|
| id | UUID | Public session ID; included as `sid` token claim |
| user | FK User | Required |
| django_session_key_hash | fixed string | Nullable, unique when present |
| status | enum | `active`, `revoked`, `expired` |
| device_label | string | Derived bounded browser/platform label |
| user_agent | string | Bounded sanitized source |
| initial_ip_hash | fixed string | Optional keyed hash |
| last_ip_hash | fixed string | Optional keyed hash |
| created_at | datetime | Required |
| last_seen_at | datetime | Updated at a bounded interval, not every read |
| expires_at | datetime | Maximum refresh/session expiry |
| revoked_at | datetime | Nullable |
| revoked_by | nullable FK User | Self/admin/security process |
| revoke_reason | string | Required for admin/system revocation |

### Constraints and Indexes

- Index `(user, status, last_seen_at desc)`.
- Index `(status, expires_at)`.
- A revoked or expired session never returns to active.
- A token `sid` and authenticated user must match the same active session.
- `last_seen_at` updates no more frequently than a configured interval to avoid
  a write on every request.

### Token Relationship

- Login creates `AccountSession`, Django session, and refresh token together.
- Refresh/access tokens include `sid`.
- Refresh rotation preserves `sid`; OutstandingToken/BlacklistedToken remain
  token-level evidence.
- Revocation marks `AccountSession` first, blacklists available refresh tokens
  for its `sid`, and deletes the associated Django session.
- Password recovery revokes every active session.
- Normal password/email changes may issue a replacement current session only
  after all previous sessions are revoked.

## 4. ResearchProject Additions

Existing `advisor` remains the canonical primary-advisor FK.

### Added Fields

| Field | Type | Rules |
|---|---|---|
| governance_state | enum | `normal`, `hold`; default `normal` |
| governance_hold_reason | enum | blank unless held; `owner_ineligible`, `legacy_admin_owner`, `migration_conflict`, `manual_correction` |
| governance_hold_started_at | datetime | Required when held |
| governance_hold_resolved_at | datetime | Nullable |
| governance_hold_resolved_by | nullable FK User | Administrator only |
| governance_hold_resolution_reason | text | Required on resolution |
| governance_version | positive integer | Optimistic concurrency, default 1 |

### Invariants

- In `normal`, `advisor` is active, email-verified, globally approved as
  teacher, and has one active `advisor` membership.
- In `hold`, the legacy `advisor` reference remains for evidence even when
  ineligible; ownership/membership/destructive governance writes are blocked
  except administrator resolution.
- Resolution locks project and candidate teacher, re-checks eligibility,
  transfers ownership, normalizes memberships, increments version, and records
  audit evidence atomically.

### State Transitions

```text
normal -> hold       owner becomes ineligible or migration detects invalid owner
hold -> normal       administrator assigns eligible successor with reason
hold -> hold         idempotent observation only; no governance mutation
```

## 5. ProjectMembership Changes

### Role Values

| Stored role | Business label | Eligibility |
|---|---|---|
| advisor | Primary advisor | Active, verified, approved teacher |
| co_advisor | Co-advisor | Active, verified, approved teacher |
| reviewer | Reviewer | Active, verified, approved teacher |
| observer | Observer | Active, verified, approved teacher |
| student | Student | Active approved student |

`advisor` is retained for backward compatibility; the UI and new contracts call
it `primary_advisor`.

### Added Fields

| Field | Type | Rules |
|---|---|---|
| assigned_by | nullable FK User | Backfilled where known |
| assignment_reason | text | Required for administrator intervention |
| role_changed_at | datetime | Nullable |
| version | positive integer | Optimistic concurrency, default 1 |

### Constraints and Indexes

- Existing one-active-membership-per-project/user constraint remains.
- Partial unique constraint: one active `advisor` membership per project.
- Index `(project, role, status)`.
- Index `(user, role, status)`.
- Administrators cannot hold a membership.
- Role change locks membership/project/target account, validates eligibility,
  increments version, and creates an audit event in one transaction.

## 6. ProjectOwnershipTransfer

Immutable evidence and idempotency record for ownership transfer.

| Field | Type | Rules |
|---|---|---|
| id | UUID | Public identifier |
| project | FK ResearchProject | Required |
| previous_advisor | FK User | Required |
| new_advisor | FK User | Required, eligible at commit |
| previous_advisor_result | enum | `co_advisor`, `reviewer`, `observer`, `removed` |
| initiated_by | FK User | Primary advisor or administrator |
| reason | text | Required for admin/hold resolution; optional otherwise |
| expected_project_version | integer | Required concurrency token |
| completed_at | datetime | Required |

### Constraints

- Previous and new advisor differ.
- Unique idempotency key may be supplied per transfer request.
- The transfer and matching membership updates are atomic.
- History is never edited or deleted through ordinary workflows.

## 7. SubmissionReviewAssignment

Explicit reviewer access to one submission target.

### Fields

| Field | Type | Rules |
|---|---|---|
| id | UUID | Public identifier |
| project | FK ResearchProject | Required denormalized scope |
| reviewer_membership | FK ProjectMembership | Active reviewer role |
| weekly_report | nullable FK WeeklyProgressReport | One possible target |
| writing_version | nullable FK WritingVersion | One possible target |
| draft_version | nullable FK DraftVersion | Legacy target |
| status | enum | `active`, `removed` |
| assigned_by | FK User | Primary/co-advisor or admin |
| assigned_at | datetime | Required |
| removed_by | nullable FK User | Required when removed |
| removed_at | datetime | Nullable |
| version | positive integer | Optimistic concurrency |

### Constraints and Indexes

- Check constraint: exactly one target FK is non-null.
- Target project must equal assignment project.
- Reviewer membership project must equal assignment project.
- Unique active assignment per reviewer and target.
- Index `(reviewer_membership, status, assigned_at desc)`.
- Per-target indexes for active review queues.

### Access Rule

Reviewer project membership allows project overview, tasks, and permitted
materials. Only an active target assignment allows submission/comment detail
and feedback writes for that target. Removing either membership or assignment
revokes target access on the next request.

## 8. AuditEvent Additions

Existing event rows remain valid.

### Added Fields

| Field | Type | Rules |
|---|---|---|
| category | enum/string | `account_security`, `account_governance`, `project_governance`, `submission_review`, `material`, `resource`, `schedule`, `notification`, `audit_access`, `release_governance`, `other` |
| outcome | enum | `succeeded`, `denied`, `failed`, `queued` |
| reason | text | Sanitized business reason; blank when not applicable |
| correlation_id | UUID/string | Existing request ID where available |
| actor_snapshot | JSON object | Allowlisted id/email/name/role snapshot |
| redaction_version | positive integer | Sanitizer policy version |

### Existing Fields Retained

`project`, `actor`, `event_type`, `target_type`, `target_id`,
`target_snapshot`, `summary`, `created_at`.

### Indexes

- `(created_at desc, id desc)` for cursor pagination.
- `(category, created_at desc)`.
- `(outcome, created_at desc)`.
- `(actor, created_at desc)`.
- `(project, created_at desc)`.
- `(target_type, target_id, created_at desc)`.
- `correlation_id`.

### Redaction Contract

Only action-specific allowlisted snapshot keys persist. Recursive deny rules
remove password, token, code, cookie, authorization, session credential,
uploaded bytes/content, and private request-body keys. Strings are length
bounded. Redaction occurs before database persistence and again before
serialization/export.

## 9. AuditExport

Tracks one bounded, attributable export.

| Field | Type | Rules |
|---|---|---|
| id | UUID | Public identifier |
| requested_by | FK User | Administrator |
| status | enum | `queued`, `processing`, `ready`, `failed`, `expired` |
| filter_snapshot | JSON object | Normalized allowlisted filters |
| high_water_event_id | bigint | Maximum included event at request time |
| requested_count | integer | Count at request time, max 10,000 |
| exported_count | integer | Set on completion |
| file | nullable FK UploadedFile | CSV artifact |
| checksum_sha256 | fixed string | Set on completion |
| failure_reason | text | Sanitized/operator-safe |
| created_at | datetime | Required |
| started_at | datetime | Nullable |
| completed_at | datetime | Nullable |
| expires_at | datetime | Required |

### Constraints and Lifecycle

```text
queued -> processing -> ready -> expired
queued -> failed
processing -> failed
failed -> queued       bounded operator retry
```

- Requested count must be `1..10000`; empty/excess filters are rejected.
- Worker claims jobs atomically and streams by cursor/chunks.
- Download requires current administrator status and export owner or explicit
  global export capability; this feature uses owner-only download.
- Ready files expire and are removed; AuditEvent rows and export evidence remain.

## 10. Repository AcceptancePolicy

Stored at `.specify/acceptance-policy.json` and validated by
`contracts/acceptance.schema.json` definitions.

| Field | Rules |
|---|---|
| schemaVersion | Required supported version |
| disciplines | Exactly `product`, `testing`, `development` |
| allowedReviewers | Non-empty repository identity list per discipline |
| exceptionApprovers | Non-empty repository identity list |
| maxExceptionDays | Integer `1..14` |
| normativeSections | Fixed checker-owned identifiers; policy cannot omit mandatory sections |

Policy changes require protected review and cannot make an already-invalid
acceptance valid without a new release evaluation.

## 11. Repository FeatureAcceptance

Stored as `specs/<feature>/acceptance.json`.

### Fields

| Field | Rules |
|---|---|
| schemaVersion | Required |
| feature | Must match directory |
| specificationPath | Must resolve inside feature directory |
| normativeRevision | SHA-256 of canonical normative sections |
| decisions | Exactly one current decision per required discipline |
| exceptions | Zero or more append-only exception decisions |
| lastEvaluatedAt | Informational; not trusted for release |

Each decision contains discipline, assigned reviewer, decision
`pending|accepted|rejected`, decided revision, decided time, and rationale.
Staleness is computed when `decidedRevision != normativeRevision`; it is not a
manually trusted flag.

Each exception contains ID, owner, distinct approver, covered disciplines,
feature/revision/release scope, reason, approved/revoked timestamps, and expiry
no later than 14 days after approval.

## 12. ReleaseEligibilityResult

Generated output, not authoritative input.

| Field | Rules |
|---|---|
| feature | Required |
| normativeRevision | Current computed revision |
| releaseScope | Requested immutable release identifier |
| result | `eligible` or `blocked` |
| decisions | Valid/stale/rejected/pending state per discipline |
| appliedException | Nullable exact exception ID |
| blockers | Stable machine-readable codes plus safe messages |
| evaluatedAt | UTC timestamp |

The checker exits non-zero for blocked/malformed/unavailable evidence and emits
both JSON output for automation and concise text for operators.

## Migration Sequence

1. Add account security/session tables and indexes.
2. Deploy token/session code in compatibility mode; create sessions on new
   login and reject legacy refresh rotation.
3. Add project governance fields, `co_advisor`, membership evidence/version,
   ownership transfer, and review assignment.
4. Data migration:
   - Normalize duplicate/removed advisor memberships.
   - Eligible teacher owner: ensure one active `advisor` membership.
   - Administrator/ineligible/missing owner: set governance hold and report.
   - Preserve all student memberships and project content.
5. Add audit columns/indexes and export table; backfill category/outcome/
   redaction version conservatively for historical events.
6. Deploy runtime APIs/UI and export worker.
7. Add acceptance schema/policy/checker in reporting mode.
8. Create acceptance files for tracked governed features as pending.
9. Enable production release enforcement after reviewer policy and repository
   protection are configured.

## Rollback Rules

- Never reverse consumed/superseded recovery or verified email-change evidence.
- Never reactivate sessions; older code may ignore the registry, so rollback
  requires global refresh-token blacklist/session flush and re-login.
- Keep `co_advisor`, hold, ownership history, assignments, audit additions, and
  exports tables even if UI/routes are disabled.
- Do not convert held projects back to normal automatically.
- Keep acceptance files and checker reports; disabling enforcement requires a
  reviewed rollback change, not an environment bypass.
- Verify backup restore preserves session revocations, project holds, audit
  rows, and acceptance artifacts.
