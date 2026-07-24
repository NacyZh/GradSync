# Quickstart: Access and Release Governance

## Prerequisites

- Python 3.12 environment at `.venv` with backend development dependencies.
- Frontend dependencies installed under `frontend/`.
- PostgreSQL and Redis for CI-equivalent integration runs.
- Existing email backend configured; local validation may use the console email
  backend.

Before implementation or deployment, back up the database and generate a
dry-run report identifying eligible teacher-owned projects and projects that
will enter governance hold.

## Configuration

Document and provide safe defaults for:

```dotenv
GRADSYNC_RECOVERY_TOKEN_TTL_SECONDS=1800
GRADSYNC_EMAIL_CHANGE_TOKEN_TTL_SECONDS=1800
GRADSYNC_RECOVERY_THROTTLE_RATE=5/hour
GRADSYNC_APPROVED_FRONTEND_ORIGIN=https://gradsync.example.edu
GRADSYNC_AUDIT_RETENTION_DAYS=365
GRADSYNC_AUDIT_EXPORT_MAX_ROWS=10000
GRADSYNC_AUDIT_EXPORT_TTL_SECONDS=86400
```

The application must fail closed when the approved recovery origin is invalid
or when required audit/acceptance evidence cannot be persisted or evaluated.

## Focused Validation

Run migrations and backend checks:

```bash
cd backend
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py migrate --plan
../.venv/bin/pytest tests/unit tests/contract tests/integration
../.venv/bin/ruff check .
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

Run OpenAPI drift and generated-artifact checks from the repository root:

```bash
bash scripts/check-openapi-contract.sh \
  specs/016-access-governance/contracts/openapi.yaml
sh scripts/check-generated-artifacts.sh --clean
```

Run acceptance checker fixtures before enabling release enforcement:

```bash
python3 scripts/check-spec-acceptance.py \
  --feature 016-access-governance \
  --mode report
python3 scripts/check-spec-acceptance.py \
  --feature 016-access-governance \
  --scope production \
  --mode enforce
```

`--report` is diagnostic and must identify pending, rejected, stale, and
exception-covered disciplines. `--enforce` must return non-zero unless all
three disciplines accept the current normative revision or a current,
revision-bound exception covers every unresolved discipline.

## Acceptance Journeys

### 1. Recovery and Replay Safety

1. Request recovery for existing, unknown, inactive, and unverified addresses.
2. Confirm identical public responses and bounded response time.
3. Consume one valid link and verify all account sessions are revoked.
4. Retry the consumed link and two concurrent submissions; exactly one may
   succeed.
5. Confirm audit records contain outcome and correlation data but no token,
   password, full cookie, or authorization header.

Expected: AC-001..004 and AC-012 pass.

### 2. Email and Session Lifecycle

1. Request an email change with the correct current password.
2. Verify the new address, including a uniqueness race.
3. List active browser/JWT sessions, revoke one other session, then revoke all
   others.
4. Exercise the revoked cookie and token on the next protected request.

Expected: the old email remains active until verification, duplicate ownership
is rejected atomically, and revoked sessions fail immediately (AC-003..006).

### 3. Collaborator Roles and Governance Hold

1. Search teachers from a 10,000-account fixture and verify at most 25 active,
   verified, approved teachers are returned.
2. Add co-advisor, reviewer, and observer roles; confirm each role matrix in
   the frontend and API.
3. Remove or deactivate the sole primary advisor and verify the project enters
   governance hold while permitted non-destructive work remains available.
4. As administrator, transfer ownership to an eligible teacher and verify the
   hold clears with an immutable audit trail.

Expected: AC-007..010 and AC-013 pass. Administrators never acquire ownership
or membership.

### 4. Target-Specific Review

1. Assign one report or writing version to one or more reviewers.
2. Verify a reviewer can open that target, its revision history, and connected
   inline comments.
3. Verify the same reviewer cannot enumerate or open an unassigned target.
4. Remove the assignment and repeat the protected request.

Expected: access is removed on the next request and hidden metadata does not
leak (AC-008..010).

### 5. Audit Search and Export

1. Seed at least 100,000 audit events across categories, actors, outcomes,
   targets, and correlation IDs.
2. Filter with cursor pagination and inspect event details.
3. Request an export exceeding 10,000 matching rows and verify it is capped,
   asynchronous, status-visible, authorized, and expires.
4. Search the API response and CSV for recovery tokens, passwords, cookies,
   authorization values, and unapproved personal fields.

Expected: list p95 remains below two seconds, export completes below 60 seconds,
and redaction is applied at write time (AC-011..015).

### 6. Acceptance and Exception Governance

1. Accept the current normative revision independently for Product, Testing,
   and Development, including one account completing more than one discipline.
2. Change only non-normative formatting; verify decisions stay current.
3. Change a normative section; verify all old decisions become stale.
4. Test pending, rejection, stale, expired exception, revoked exception,
   mismatched revision/scope, and same owner/approver fixtures.
5. Verify reporting jobs remain diagnostic while production release blocks
   before image publication/deployment.

Expected: AC-016..018 pass deterministically from a clean checkout.

### 7. Migration and Rollback

1. Migrate a production-shaped copy with teacher-owned, administrator-owned,
   ineligible-owner, duplicate-advisor, and ordinary student memberships.
2. Verify eligible owners become primary-advisor memberships and all other
   problematic ownership enters a reported hold.
3. Exercise rollback by disabling new routes and gates while retaining additive
   schema, audit evidence, acceptance files, revocations, and holds.

Expected: no project, account, student membership, or audit row is lost
(AC-013, AC-015, AC-020).

### 8. UI, Locale, and Accessibility

Run Playwright journeys at 390px, 900px, and 1440px for both locales:

```bash
cd frontend
GRADSYNC_E2E_MODE=fullstack \
GRADSYNC_BACKEND_PYTHON=../.venv/bin/python \
npm run test:e2e -- auth-login.spec.ts role-workspaces.spec.ts \
  collaboration-project-members.spec.ts accessibility.spec.ts \
  production-ui.spec.ts
```

Expected: no clipped/overlapping primary UI, account comboboxes remain
input-driven, dialogs/sheets are keyboard-complete, role-forbidden controls are
absent, and mutation feedback uses global toast (AC-005, AC-007, AC-010,
AC-014, AC-019).

## Production Gate Order

1. Build and test backend/frontend artifacts.
2. Validate OpenAPI and generated artifacts.
3. Evaluate the current normative fingerprint and acceptance evidence.
4. Block on invalid, pending, rejected, stale, or uncovered decisions.
5. Publish images only after the production acceptance gate succeeds.
6. Migrate with backup, hold report, worker/readiness checks, and smoke tests.

Rollback must never reactivate a revoked session, restore a removed role,
clear a governance hold without transfer evidence, mutate audit history, or
discard acceptance evidence.

## Implementation Validation Record

Validated on 2026-07-24:

- Django migration generation and the isolated migration plan completed
  without model drift.
- Backend unit, contract, and integration suites passed: 489 tests.
- Ruff, ESLint, TypeScript, Vite build, and all 184 frontend component tests
  passed.
- The feature OpenAPI contract covered all 25 operations with zero schema
  errors; the repository's existing schema-generator warning baseline remains
  visible.
- Acceptance-policy fixtures passed: 8 tests. Generated-artifact validation
  passed from a clean build-output state.
- Full-stack Playwright passed 70 scenarios with 39 mock-only scenarios
  skipped; the mock suite passed all 109 scenarios.
- Production readiness and acceptance enforcement correctly stopped before
  runtime mutation because Product, Testing, and Development decisions for the
  current normative revision remain Pending.
