# Quickstart: Research Group Operations

## Purpose

Validate the planned GradSync implementation end-to-end against the feature
specification, data model, and API contract.

## Prerequisites

- Docker Compose available on the host
- Environment variables configured for database credentials, email delivery, and
  application secrets
- Test users for at least one advisor and two students

## Setup

1. Build and start the application stack:

   ```bash
   docker compose up --build
   ```

2. Run database migrations and seed validation data:

   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py seed_demo_research_ops
   ```

3. Run automated checks:

   ```bash
   docker compose exec backend pytest
   docker compose exec frontend npm test
   docker compose exec frontend npm run test:e2e
   ```

## Validation Scenarios

### Scenario 1: Project Isolation and Hierarchical Tasks

1. Sign in as an advisor.
2. Create Project A with Student A and Project B with Student B.
3. Add a three-level task hierarchy to Project A with deadlines and assignees.
4. Sign in as Student A and confirm Project A tasks are visible.
5. Confirm Project B tasks, drafts, reports, comments, bookings, notifications,
   and activity are not visible or searchable.

**Expected outcome**: Project records remain isolated by project membership, and
task hierarchy is visible only in the correct project context.

### Scenario 2: Draft Versions and Inline Comments

1. Sign in as Student A and submit Draft Version 1 for Project A.
2. Sign in as the advisor and add inline comments to Version 1.
3. Sign in as Student A and submit Draft Version 2.
4. Confirm comments remain attached to Version 1 and Version 2 starts with a new
   pending review status.

**Expected outcome**: Draft versions are preserved, comments do not drift across
versions, and the advisor receives a new submission notification.

### Scenario 3: Weekly Progress Report Review

1. Sign in as Student A and submit the current week's progress report for
   Project A.
2. Sign in as the advisor and add inline comments.
3. Mark the report as needing revision.
4. Confirm Student A can see the comments and review status in Project A only.

**Expected outcome**: Weekly reports are project-scoped, review status changes
are visible, and inline comments remain attached to the report.

### Scenario 4: Resource Booking Conflict

1. Sign in as Student A and reserve a lab seat for Project A from 10:00 to 11:00.
2. Sign in as another authorized project member and attempt to reserve the same
   seat from 10:30 to 11:30.
3. Try a non-overlapping reservation for the same seat.

**Expected outcome**: The overlapping reservation is rejected with a clear
message, and the non-overlapping reservation succeeds.

### Scenario 5: Notification Processing

1. Submit a draft and a weekly report.
2. Create a task deadline inside the approaching-deadline reminder window.
3. Leave one submission pending past the pending-review reminder window.
4. Run the worker and scheduler services.
5. Inspect notification records and the configured email sink.

**Expected outcome**: New submission, approaching deadline, pending review, and
booking change notifications create visible delivery records within 5 minutes of
eligibility.

### Scenario 6: Archived Project Read-Only Behavior

1. Archive Project A as the advisor.
2. Attempt to add a task, submit a draft, submit a report, add a comment, and
   create a booking.
3. Reopen the project and repeat one allowed action.

**Expected outcome**: Archived projects remain readable but block new records
until reopened.

## Contract References

- API contract: [contracts/openapi.yaml](./contracts/openapi.yaml)
- Data model: [data-model.md](./data-model.md)
- Feature specification: [spec.md](./spec.md)

## Performance Validation

Seed a project with 500 active records and confirm:

- Project dashboard opens within 3 seconds.
- Project-scoped search/filter completes within 2 seconds.
- Common record updates show visible confirmation within 2 seconds.
- Eligible reminder notifications create visible records within 5 minutes.
