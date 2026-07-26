# US1 Notification Loop Checkpoint

**Recorded**: 2026-07-24
**Scope**: Phase 1, Phase 2, and User Story 1 only

## Acceptance Evidence

- [x] AC-001: Delivery, read, acknowledgement, authoritative completion,
  expiry, unavailable, retry, and terminal outcomes have independent tests.
- [x] AC-002: Notification list filters, selected-ID reads, cursor/page-size
  bounds, mixed-recipient isolation, and 1,000-record pagination pass.
- [x] AC-003: Active follow-up deduplication, authoritative resolver
  reconciliation, project event typing, and live query invalidation pass.
- [x] AC-004: Quiet hours, timezone handling, category email settings,
  mandatory security delivery, bounded project policy, reminders, and
  escalation pass.
- [x] AC-012: The eight-actor execution capability matrix and primary-advisor
  notification-policy authority pass.
- [x] AC-013: Notification acknowledgement and policy changes create
  attributable, redacted audit evidence; admin summaries expose counts only.
- [x] AC-014: The notification drawer remains bounded at 390, 900, and 1440
  pixels and exposes keyboard-accessible controls.
- [x] AC-015: English and Chinese notification lifecycle, preference, and
  project-policy catalogs pass locale completeness tests.
- [x] AC-016: Email failure retains in-app delivery, masks failure detail,
  retries with bounded attempts, and exposes count/lag metrics.

## Automated Results

- [x] Backend full suite: `521 passed`.
- [x] Frontend component suite: `186 passed`.
- [x] Notification E2E suite: `4 passed`.
- [x] US1 focused backend checkpoint: `10 passed`.
- [x] Acceptance checker regression suite: `10 passed`.
- [x] Production frontend build and ESLint: passed.
- [x] Django migration drift and system checks: passed.
- [x] OpenAPI generation: `Errors: 0`; repository-wide legacy warnings remain.
- [x] Notification performance: 1,000 records, 100-item bounded page, under
  three seconds with at most eight database queries.

## Governance State

Feature 017 acceptance evidence remains intentionally `pending` for product,
testing, and development. Validation mode accepts the evidence shape while
production enforcement remains blocked until the maintainer explicitly accepts
the current normative revision.
