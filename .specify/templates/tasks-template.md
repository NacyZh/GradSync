---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Automated tests are required for every behavioral change. Include the
lowest useful test level for each story, plus integration or end-to-end coverage
when behavior crosses modules, persistence, network boundaries, authorization,
background jobs, operational checks, or UI workflows. If a test gap is approved
in plan.md, include the documented reason, owner, expiry date, and release risk.
Tests MUST be written before business implementation tasks and should fail first
for the missing behavior unless an approved plan exception exists.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] [Area] Description (AC: AC-###)`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[Area]**: Ownership area such as Backend, Frontend, Test, Docs, Ops, CI
- **AC**: Specification acceptance criterion or plan gate the task proves
- Include exact file paths in descriptions
- Keep each task small enough to complete in 8 hours or less; split larger work
- Include a concrete self-check expectation in each task description or
  sub-bullet

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Acceptance criteria from spec.md
  - Constitution Check gates from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools
- [ ] T004 [P] Document local environment and test commands in README or docs
  self-check: command snippets are runnable and match plan.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T005 Setup database schema and migrations framework (AC: foundational)
- [ ] T006 [P] Implement authentication/authorization framework (AC: security)
- [ ] T007 [P] Setup API routing and middleware structure (AC: contracts)
- [ ] T008 Create base models/entities that all stories depend on (AC: data-model)
- [ ] T009 Configure structured error handling, request IDs, and logging infrastructure (AC: ops)
- [ ] T010 Setup environment configuration, secret validation, and unsafe-default checks (AC: security)
- [ ] T011 [P] Configure health/readiness checks and metrics/alert signal foundations (AC: ops)
- [ ] T012 [P] Establish migration, backup/restore, rollback, and release-smoke scaffolding as needed (AC: ops)
- [ ] T013 [P] Configure generated-artifact and spec/plan/tasks structure CI guard (AC: CI)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] [Test] Contract test for [endpoint] in tests/contract/test_[name].py (AC: AC-###)
  self-check: fails before endpoint implementation
- [ ] T015 [P] [US1] [Test] Integration test for [user journey] in tests/integration/test_[name].py (AC: AC-###)
  self-check: covers normal, exception, and boundary paths
- [ ] T016 [P] [US1] [Test] Security/isolation test for [boundary] in tests/integration/test_[name].py (AC: SEC-###)
  self-check: proves unauthorized access is rejected

### Implementation for User Story 1

- [ ] T017 [P] [US1] [Backend] Create [Entity1] model in src/models/[entity1].py (AC: AC-###)
- [ ] T018 [P] [US1] [Backend] Create [Entity2] model in src/models/[entity2].py (AC: AC-###)
- [ ] T019 [US1] [Backend] Implement business service in src/services/[service].py (depends on T017, T018) (AC: AC-###)
- [ ] T020 [US1] [Backend] Implement endpoint/feature in src/[location]/[file].py (AC: AC-###)
- [ ] T021 [US1] [Backend] Add input validation, authorization, and error handling (AC: SEC-###)
- [ ] T022 [US1] [Ops] Add structured logging/audit signal for user story 1 operations (AC: OPS-###)
- [ ] T023 [US1] [Frontend] Validate UX consistency/accessibility for [changed flow] if user-facing (AC: UX-###)
- [ ] T024 [US1] [Test] Validate performance and reliability target for [journey/action] (AC: PERF-###)
- [ ] T025 [US1] [Ops] Update release/readiness checks for deployment-impacting behavior if applicable (AC: OPS-###)
- [ ] T026 [US1] [Docs] Update relevant docs/contracts for implemented behavior (AC: docs)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 ⚠️

- [ ] T027 [P] [US2] [Test] Contract test for [endpoint] in tests/contract/test_[name].py (AC: AC-###)
- [ ] T028 [P] [US2] [Test] Integration test for [user journey] in tests/integration/test_[name].py (AC: AC-###)
- [ ] T029 [P] [US2] [Test] Security/isolation test for [boundary] in tests/integration/test_[name].py (AC: SEC-###)

### Implementation for User Story 2

- [ ] T030 [P] [US2] [Backend] Create [Entity] model in src/models/[entity].py (AC: AC-###)
- [ ] T031 [US2] [Backend] Implement [Service] in src/services/[service].py (AC: AC-###)
- [ ] T032 [US2] [Backend] Implement [endpoint/feature] in src/[location]/[file].py (AC: AC-###)
- [ ] T033 [US2] [Backend] Integrate with User Story 1 components if needed (AC: AC-###)
- [ ] T034 [US2] [Ops] Add structured logging/audit signal for user story 2 operations (AC: OPS-###)
- [ ] T035 [US2] [Frontend] Validate UX consistency/accessibility for [changed flow] if user-facing (AC: UX-###)
- [ ] T036 [US2] [Test] Validate performance and reliability target for [journey/action] (AC: PERF-###)
- [ ] T037 [US2] [Ops] Update release/readiness checks for deployment-impacting behavior if applicable (AC: OPS-###)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 ⚠️

- [ ] T038 [P] [US3] [Test] Contract test for [endpoint] in tests/contract/test_[name].py (AC: AC-###)
- [ ] T039 [P] [US3] [Test] Integration test for [user journey] in tests/integration/test_[name].py (AC: AC-###)
- [ ] T040 [P] [US3] [Test] Security/isolation test for [boundary] in tests/integration/test_[name].py (AC: SEC-###)

### Implementation for User Story 3

- [ ] T041 [P] [US3] [Backend] Create [Entity] model in src/models/[entity].py (AC: AC-###)
- [ ] T042 [US3] [Backend] Implement [Service] in src/services/[service].py (AC: AC-###)
- [ ] T043 [US3] [Backend] Implement [endpoint/feature] in src/[location]/[file].py (AC: AC-###)
- [ ] T044 [US3] [Ops] Add structured logging/audit signal for user story 3 operations (AC: OPS-###)
- [ ] T045 [US3] [Frontend] Validate UX consistency/accessibility for [changed flow] if user-facing (AC: UX-###)
- [ ] T046 [US3] [Test] Validate performance and reliability target for [journey/action] (AC: PERF-###)
- [ ] T047 [US3] [Ops] Update release/readiness checks for deployment-impacting behavior if applicable (AC: OPS-###)

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Verify every task maps to spec AC and has self-check notes
- [ ] TXXX Performance and reliability validation across all stories
- [ ] TXXX [P] Additional unit tests in tests/unit/
- [ ] TXXX UX consistency and accessibility verification
- [ ] TXXX Security hardening and authorization/isolation review
- [ ] TXXX Observability review: structured logs, request IDs, metrics, alerts, and background job visibility
- [ ] TXXX Migration, backup/restore, rollback, and release-smoke validation
- [ ] TXXX Verify README, API contracts, data model docs, and third-party integration docs are current
- [ ] TXXX Run CI-equivalent checks, including spec structure, lint/format, tests, and generated-artifact guard
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation unless plan.md records
  an approved test gap with reason and owner
- Each task MUST be 8 hours or less; split any task that exceeds this
- Each task MUST include area ownership and AC or gate traceability
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
