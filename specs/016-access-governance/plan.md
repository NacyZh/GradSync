# Implementation Plan: Access and Release Governance

**Branch**: `spec/feature-016` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-access-governance/spec.md`

## Summary

Close four governance gaps without replacing GradSync's existing authentication,
project, audit, notification, or deployment stack. Add an authoritative account
session registry shared by browser sessions and JWT refresh/access tokens,
single-use email password recovery, verified email change, and per-device
revocation. Complete project collaborator roles with teacher-only selectors,
centralized capabilities, target-specific reviewer assignments, sole-owner
transfer, and governance hold. Expand immutable audit metadata into an
administrator console with cursor filtering and bounded asynchronous CSV
exports. Add repository-owned, revision-bound specification acceptance records,
deterministic normative-spec fingerprints, and CI/release gates with
time-bounded exceptions.

The design is additive except for two intentional policy corrections:
administrators supervise projects globally rather than becoming project
members/owners, and legacy sessions without an authoritative session ID cannot
be refreshed after rollout. Existing valid teacher-owned projects migrate to an
explicit primary-advisor membership; administrator-owned or otherwise
ineligible projects enter governance hold until audited transfer.

## Technical Context

**Language/Version**: Python 3.12 in CI (project supports Python 3.12+);
TypeScript 5.6; React 18.3.

**Primary Dependencies**: Existing Django 5.x, Django REST Framework,
djangorestframework-simplejwt with token blacklist, drf-spectacular, Celery
5.x, django-celery-results/beat, PostgreSQL 16, Redis 7, React Router, TanStack
Query, Radix/shadcn-style primitives, Tailwind CSS, Lucide icons. Python
standard-library JSON/hash/CSV support is used for release governance. No new
runtime dependency.

**Storage**: Existing PostgreSQL for account security records, project role
state, review assignments, audit metadata, and export jobs; existing uploaded
file/media storage for short-lived audit export files; version-controlled JSON
under `specs/` and `.specify/` for release acceptance policy and decisions.
Redis remains a Celery broker and is not authoritative for revocation,
authorization, or acceptance.

**Testing**: pytest/pytest-django unit, migration, contract, integration,
concurrency, authorization, redaction, and performance tests; drf-spectacular
OpenAPI drift checks; Ruff and migration checks; Vitest/React Testing Library,
frontend boundary/i18n tests, Playwright mocked and full-stack role/security/
responsive/accessibility journeys, TypeScript build, ESLint, PWA and generated
artifact checks; repository acceptance-checker fixture tests and release gate
smoke checks.

**Target Platform**: Existing GradSync browser application and Linux production
containers behind the current TLS/frontend proxy, with PostgreSQL, Redis,
Gunicorn, Celery worker/beat, and immutable backend/frontend images.

**Project Type**: Full-stack Django monolith plus React single-page application,
with repository-local release governance tooling.

**Performance Goals**: Meet AC-001/005/011 and PERF-001..005: 95% of recovery
acknowledgements, session lists, collaborator searches, and release evaluations
visible within 2 seconds; audit filtering over 100,000 rows visible within 2
seconds at p95; collaborator lookup bounded to 25 results over 10,000 active
accounts; exports capped at 10,000 events, entering visible processing within 2
seconds and completing within 60 seconds; revoked sessions/roles denied on the
next protected request.

**Reliability/Operations Goals**: Security and project-governance mutations are
atomic with their required audit event; recovery/email delivery exposes queued,
failed, and retryable state without leaking secrets; session and role
revocation fail closed; audit search degradation does not block ordinary reads,
but inability to persist required audit evidence rolls back privileged writes;
acceptance evidence unavailability blocks release; exports are idempotent,
bounded, expiring, and retryable; migrations preserve existing accounts,
student memberships, project data, and audit rows.

**Security/Compliance Constraints**: Generic recovery responses, scoped
throttling, hashed one-time secrets, 30-minute expiry, approved redirect
allowlist, current-password confirmation for email change, immediate
authorization/status/session checks, CSRF preservation, session ID in both
token families, no plaintext credentials in logs/audit/export, teacher-only
collaborator eligibility, explicit reviewer target assignment, admin
supervision without membership, fail-closed audit/acceptance checks, immutable
audit records for at least 365 days, and owner/approver separation for release
exceptions. No MFA, SSO, SMS recovery, guest access, or external SIEM scope.

**Constraints**: Preserve existing token refresh cookie and session-auth
compatibility, account role activation, project/material/task/report/writing
boundaries, global toast/localization patterns, OpenAPI checker, CI topology,
and production runbooks. Do not use cache-only revocation, generic foreign keys
for reviewer targets, mutable audit rows, production database state for release
approval, or new third-party auth/audit/governance services.

**Scale/Scope**: At least 10,000 active accounts, 500 visible projects, 2,000
memberships, 100,000 retained audit events, 20 concurrent authenticated users,
25 collaborator options per query, 100 audit events per page, and 10,000 rows
per export. Scope spans four user stories, approximately 15 new/changed API
operations, three new user-facing workspaces, project role adaptations across
existing feature boundaries, and one repository release gate.

**Deployment/Monitoring/Degradation**: Existing topology remains. Add
configuration for recovery/email-change TTL and throttle rates, audit retention
floor/export limit/export expiry, and approved frontend recovery origin; no new
secret beyond existing application signing/email credentials. Route audit
exports through the existing Celery default queue and expose queue age/failure
signals in readiness. Log request correlation IDs for account security,
collaboration governance, audit export, and release gate outcomes with secrets
masked. Alert on recovery throttling spikes, repeated invalid recovery
consumption, orphaned/held projects, required audit write failures, audit export
backlog/failure, and blocked production release.

**Data Migration & Rollback**: Add account recovery/email-change/session tables,
project governance fields/co-advisor role, reviewer assignment table, additive
audit fields/export table, constraints, and indexes. A data migration creates an
explicit primary-advisor membership for each eligible teacher-owned project;
administrator-owned/ineligible projects enter governance hold; duplicate
legacy advisor memberships are normalized without changing student
memberships. Legacy refresh tokens without a session ID stop rotating after
deployment and users sign in again; short-lived access tokens expire normally.
Rollback keeps additive tables/columns and acceptance/audit evidence, disables
new routes/UI/gates, and must not reactivate revoked sessions, removed roles, or
held projects. Database backup and a dry-run migration report are required
before production rollout.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **SDD Order**: PASS. `spec.md` exists, contains all five mandatory
  constitutional modules, records five closed clarifications, defines included
  and excluded scope, and has no unresolved question.
- **Review Readiness**: PASS FOR PLANNING / RELEASE BLOCKED. Product, Testing,
  and Development are recorded as Pending. This feature deliberately implements
  the structured gate; production release remains blocked until current
  revision acceptance or a valid governed exception exists.
- **Required Plan Artifacts**: PASS. This workflow produces `plan.md`,
  `research.md`, `data-model.md`, `contracts/openapi.yaml`,
  `contracts/frontend-ui.md`, `contracts/acceptance.schema.json`, and
  `quickstart.md`.
- **Technology Governance**: PASS. No new framework, database, queue, storage
  provider, or external identity service. `research.md` compares reuse of
  SimpleJWT blacklist plus an authoritative session registry, database-backed
  audit export jobs on existing Celery, and repository JSON governance against
  rejected alternatives.
- **Layering and Code Baselines**: PASS. DRF serializers/views own request
  shaping and status codes; account security, session, collaborator,
  authorization, ownership, reviewer assignment, audit redaction/export, and
  acceptance checker services own business rules; models/migrations own
  persistence/constraints/indexes; shared request ID/download/notification
  helpers remain cross-cutting; React feature modules own role-aware
  presentation. Changes are additive and existing route compatibility is
  preserved where policy allows.
- **TDD/Test Plan**: PASS AS PLAN. Before implementation: unit tests for secret
  lifecycle/session revocation, role matrix/governance hold, audit redaction,
  normative fingerprints/exceptions (AC-002/003/006/008/009/012/016..018);
  contract tests for account security, teacher search, members/ownership/review
  assignments, audit/export APIs (AC-004/005/007/013/014); migration and
  integration tests for reset concurrency, email uniqueness, dual-auth
  revocation, admin-owned project holds, atomic audit writes, export bounds,
  role leakage, and rollback (AC-001..015); frontend tests for recovery,
  sessions, collaborator selection, role-safe navigation, hold states, audit
  filters/detail/export, i18n/toast/accessibility (AC-005/007/010/019);
  release-checker fixture tests and CI smoke for accept/reject/stale/exception
  states (AC-016..018); Playwright role/security/layout workflows (AC-001/005/
  007..010/014/019/020). No test exception is approved.
- **Security Gate**: PASS. Generic public responses, throttle scopes, hashed
  secrets, expiry/replay defense, CSRF/redirect checks, authoritative session
  revocation, server-side role/target checks, concurrent locking, audit
  redaction, bounded exports, fail-closed privileged writes, immutable
  governance evidence, and release exception separation are explicit. No file
  upload is added; generated exports reuse authorized download controls.
- **Performance Gate**: PASS. Account/collaborator/audit lists are bounded and
  indexed; audit uses cursor pagination; exports are capped/chunked/async;
  search normalizes indexed fields; authorization does not rely on stale cache;
  no long export transaction; measurable p95 and completion thresholds map to
  PERF-001..005.
- **Deployment/Operations Gate**: PASS. Existing services are reused; additive
  environment values are documented with safe defaults; migration dry-run,
  backup, hold report, legacy-session re-login notice, worker/readiness checks,
  acceptance gate, smoke tests, monitoring, rollback, and evidence preservation
  are required.

## Project Structure

### Documentation (this feature)

```text
specs/016-access-governance/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── contracts/
    ├── openapi.yaml
    ├── frontend-ui.md
    └── acceptance.schema.json
```

`tasks.md` is intentionally deferred to `/speckit-tasks`.

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tokens.py
│   │   ├── authentication.py
│   │   ├── security_services.py
│   │   ├── session_services.py
│   │   └── migrations/
│   ├── projects/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── access_services.py
│   │   ├── collaboration_services.py
│   │   └── migrations/
│   ├── submissions/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── review_assignment_services.py
│   │   └── migrations/
│   ├── audit/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── export_services.py
│   │   ├── tasks.py
│   │   └── migrations/
│   └── common/
│       ├── downloads.py
│       ├── middleware.py
│       └── pagination.py
└── tests/
    ├── unit/
    ├── contract/
    └── integration/

frontend/
├── src/
│   ├── app/
│   │   └── Layout.tsx
│   ├── routes/
│   │   └── index.tsx
│   └── features/
│       ├── auth/
│       │   ├── ForgotPasswordPage.tsx
│       │   ├── ResetPasswordPage.tsx
│       │   ├── SecuritySettingsPanel.tsx
│       │   └── api.ts
│       ├── projects/
│       │   ├── ProjectCollaboratorsPanel.tsx
│       │   ├── TeacherSelector.tsx
│       │   ├── ProjectDashboardPage.tsx
│       │   └── api.ts
│       ├── submissions/
│       │   ├── ReviewerAssignmentControl.tsx
│       │   └── api.ts
│       └── admin/
│           ├── AuditConsolePage.tsx
│           ├── AuditEventDetail.tsx
│           └── api.ts
└── tests/
    ├── component/
    └── e2e/

scripts/
├── check-spec-acceptance.py
└── check-production-readiness.sh

.specify/
└── acceptance-policy.json
```

**Structure Decision**: Keep runtime ownership in existing Django apps and
React feature boundaries. Account security remains under accounts; project
roles/hold/capabilities under projects; target review assignment under
submissions; audit query/export under audit. Repository acceptance remains
outside runtime application state so CI can evaluate a checkout deterministically
before deployment. New shared code is limited to existing request correlation,
pagination, downloads, and feedback/localization patterns.

## Required Design Artifact Checklist

- [x] `research.md` records dependency research, performance/security risk
  assessment, and technology choice comparisons.
- [x] `data-model.md` records entities, field constraints, indexes,
  relationships, state transitions, and migration approach.
- [x] `contracts/openapi.yaml` records runtime frontend/backend API contracts.
- [x] `contracts/frontend-ui.md` records routes, role behavior, state, feedback,
  responsive, localization, and accessibility contracts.
- [x] `contracts/acceptance.schema.json` records repository acceptance,
  exception, and normative revision evidence.
- [x] `quickstart.md` records runnable validation scenarios aligned to AC IDs.

## Post-Design Constitution Check

- **SDD/review gates**: PASS for planning; release remains blocked by the
  specification's Pending reviewers until the governed acceptance feature is
  implemented and this revision is accepted or covered by a valid exception.
- **Artifact and clarification gates**: PASS. All required artifacts exist, all
  five clarifications are encoded, and research leaves no `NEEDS CLARIFICATION`.
- **Technology/layering gates**: PASS. Existing dependencies and domain
  boundaries are reused; no heavy dependency or cross-feature private import is
  required.
- **TDD/security/performance gates**: PASS as design. Contracts and data model
  provide testable state machines, role matrix, fail-closed paths, constraints,
  pagination/export bounds, redaction, concurrency, and performance thresholds.
- **Operations gate**: PASS as design. Additive migration, legacy-session
  degradation, backup/rollback, hold reporting, worker monitoring, acceptance
  gate ordering, and production smoke/readiness behavior are explicit.

## Complexity Tracking

No constitution violation requires an exception.
