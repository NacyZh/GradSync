# Quickstart: Research Group Operations

## Purpose

Validate the planned GradSync implementation end-to-end against the feature
specification, data model, and API contract.

## Prerequisites

- Docker Compose available on the host
- Environment variables configured for database credentials, email delivery, and
  application secrets
- Test users for at least one advisor and two students
- Local folders containing representative paper files, BibTeX/text metadata, and
  code folders or archives for import validation

Local validation accounts:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@gradsync.local` | `admin123` |
| Advisor | `advisor@example.com` | `advisor123` |
| Student | `student@example.com` | `student123` |
| Reviewer | `reviewer@example.com` | `reviewer123` |

## Setup

1. Build and start the application stack:

   ```bash
   docker compose up --build
   ```

2. Run database migrations and create validation data:

   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py seed_validation_research_ops
   ```

   The seed command creates production-shaped validation accounts, projects,
   resource types, and email-capture settings. It must not create sample copy or
   placeholder behavior in production routes.

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

### Scenario 4: Custom Resource Catalog and Booking Conflict

1. Sign in as an administrator or authorized advisor.
2. Create two resource types with different custom fields, such as a lab
   instrument type and a field-work vehicle type.
3. Create resource items for both types and confirm the custom fields render and
   validate.
4. Sign in as Student A and reserve one resource item for Project A from 10:00
   to 11:00.
5. Sign in as another authorized project member and attempt to reserve the same
   resource item from 10:30 to 11:30.
6. Try a non-overlapping reservation for the same resource item.

**Expected outcome**: The overlapping reservation is rejected with a clear
message, the non-overlapping reservation succeeds, and resource types can vary
by professional context without code changes.

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

### Scenario 7: Production Login, Frontend Architecture, and Design System

1. Start the local stack and open the unauthenticated login route on desktop and
   mobile.
2. Confirm the sign-in form is centered over a real background visual, all
   labels/errors are accessible, loading and failed-sign-in states are visible,
   and no sample account copy is shown.
3. Sign in as admin, advisor, student, and reviewer.
4. Navigate through the authenticated workspace shell on desktop, tablet, and
   mobile viewport widths.
5. Confirm role-aware navigation, selected-project context, notification entry,
   theme toggle, loading states, empty states, validation errors, and destructive
   confirmation dialogs use Tailwind CSS tokens and shadcn/ui components rather
   than ad hoc prototype controls.
6. Confirm the admin account workspace can filter accounts by role/status and
   expose suspend, reactivate, and archive controls without leaking those routes
   to advisor or student users.
7. Confirm project dashboard, review queue, booking workspace, notification
   center, and account administration routes load through route-level bundles
   and preserve selected-project context before create, submit, review, comment,
   book, cancel, archive, or reopen actions.
8. Complete project creation, task update, draft/report submission, review
   status update, inline comment creation, booking creation, booking
   cancellation, archive, and reopen workflows using keyboard navigation only.
9. Run component, accessibility, build, full-stack Playwright, and production UI
   screenshot/layout checks:

   ```bash
   sh scripts/check-generated-artifacts.sh
   cd frontend
   npm run lint
   npm test
   GRADSYNC_E2E_MODE=fullstack npm run test:e2e
   npm run test:e2e -- production-ui.spec.ts
   npm run build
   ```

**Expected outcome**: The frontend behaves as a production operations workspace
with consistent layout, accessible controls, stable project context,
recoverable feedback, route-level workspace bundles, ignored generated
artifacts, centered production login, and no placeholder surfaces.

### Scenario 8: Paper Team Library Local Import, Deduplication, Search, and Download

1. Sign in as an advisor or project member for Project A.
2. Open Project A's paper library.
3. Select a local folder containing one new paper and one duplicate represented
   by the same supplied DOI or normalized title, first author, and publication
   year.
4. Confirm the import preview shows accepted, duplicate, and error counts with a
   clear duplicate match reason.
5. Commit the accepted item and search by title, author, venue, year, tag, and
   DOI.
6. Download the authorized paper attachment and inspect the project activity or
   audit trail.
7. Confirm no automatic external paper search, DOI lookup, or online discovery
   was triggered during import.
8. Sign in as a member of unrelated Project B and confirm Project A papers and
   downloads are not visible or searchable.
9. Run the focused automated validation:

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/contract/test_papers_api.py tests/unit/test_paper_duplicate_rules.py tests/integration/test_research_assets_project_scope.py
   ```

**Expected outcome**: Local paper imports reject duplicates with explainable
matches, paper search is project-scoped and explicit, downloads require current
authorization, and download activity is audit-visible.

### Scenario 9: Project Code Team Library Local Import, Versioning, Search, and Download

1. Sign in as a Project A member.
2. Open Project A's code library workspace.
3. Select a local code folder or archive and create a code artifact with tags,
   version label or commit reference, checksum, description, and release notes.
4. Attempt to import another active version with a duplicate checksum or version
   label.
5. Search/filter by name, tag, uploader, version label, and commit reference.
6. Download the authorized version and inspect the project activity or audit
   trail.
7. Confirm no automatic repository search or background discovery was triggered.
8. Sign in as a member of unrelated Project B and confirm Project A code
   artifacts and downloads are not visible or searchable.
9. Run the focused automated validation:

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/contract/test_code_artifacts_api.py tests/unit/test_code_artifact_rules.py
   ```

**Expected outcome**: Code artifacts remain project-scoped team-library records,
duplicate version/checksum conflicts are explained, versions can be searched and
downloaded by authorized members, descriptions are preserved, and downloads are
audit-visible.

### Scenario 10: Chinese and English Language Switching

1. Sign in and open the authenticated workspace shell.
2. Switch the language from English to Chinese.
3. Confirm navigation, project context, form labels, validation messages, empty
   states, confirmations, paper library labels, code library labels, and status
   feedback update immediately in Chinese without a full page reload while
   user-generated research content remains unchanged.
4. Navigate to a project route, start filling a form, and switch back to English.
5. Confirm the route, selected project context, focus order, unsaved-form
   warning, and authorization state are preserved.
6. Sign out and sign in again; confirm the selected language preference persists.
7. Run the focused automated validation:

   ```bash
   cd backend
   ../.venv/bin/python -m pytest tests/contract/test_locale_api.py
   cd ../frontend
   npm test -- --run tests/component/research-assets-locale.test.tsx
   npm run test:e2e -- research-assets-locale.spec.ts
   ```

**Expected outcome**: The interface can switch between Chinese and English
without losing workflow context, changing stored research content, or weakening
authorization.

### Scenario 11: Email System and Delivery Status

1. Configure local email capture or SMTP environment variables.
2. Submit a draft, submit a weekly report, create a booking change, and create a
   deadline inside the reminder window.
3. Run worker and scheduler services.
4. Inspect the notification center, backend notification records, and email
   capture mailbox.
5. Temporarily force a delivery failure and confirm the failed status is visible
   without leaking credentials.

**Expected outcome**: Email notifications are queued, sent, failed, or skipped
with visible status records, retryable failures can be retried safely, and
project membership is re-checked before send.

## Contract References

- API contract: [contracts/openapi.yaml](./contracts/openapi.yaml)
- Frontend UI contract: [contracts/frontend-ui.md](./contracts/frontend-ui.md)
- Data model: [data-model.md](./data-model.md)
- Feature specification: [spec.md](./spec.md)

## Performance Validation

Seed a project with 500 active records and confirm:

- Project dashboard opens within 3 seconds.
- Project-scoped search/filter completes within 2 seconds.
- Paper/code library search/filter completes within 2 seconds for up to 1,000
  papers and 250 code artifacts in one project.
- Duplicate detection for 100 locally imported paper metadata records completes
  within 10 seconds before commit.
- Common record updates show visible confirmation within 2 seconds.
- Eligible reminder notifications create visible records within 5 minutes.
