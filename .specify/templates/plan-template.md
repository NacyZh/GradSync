# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Reliability/Operations Goals**: [health/readiness, queue timing, backup/restore, rollback, observability, or N/A]

**Security/Compliance Constraints**: [auth, authorization, data isolation, secrets, transport, audit, or N/A]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Production-Grade Code Quality**: Identify affected modules, ownership
  boundaries, documentation needs, linting/formatting/type expectations,
  migration needs, configuration validation, and any new abstraction with its
  justification.
- **Tests Prove Releasability**: Define required automated tests by level (unit,
  contract, integration, end-to-end, readiness/smoke) and map them to user
  stories, service contracts, edge cases, security boundaries, data changes, or
  operational checks. Document any test gap with reason, owner, expiry date, and
  release risk.
- **Operable User Experience**: For user-facing work, record existing UX
  patterns to preserve, responsive behavior, accessibility checks, required
  loading/empty/success/error states, and recoverable feedback for persistence,
  permission, notification, or background-job failures.
- **Measured Performance and Reliability**: Define measurable targets and
  validation methods for affected journeys, including latency, throughput,
  memory, bundle size, rendering metrics, queue timing, health/readiness,
  recovery objectives, or availability signals where relevant.
- **Secure, Observable, Maintainable Architecture**: Confirm the design uses
  existing project patterns and shared concerns for validation, authorization,
  project isolation, logging, error handling, configuration, secret management,
  health checks, metrics, backups, migrations, and rollback. Record any added
  service, framework, state store, persistence pattern, or cross-cutting
  deviation in Complexity Tracking.
- **Production Deployment Readiness**: Record deployment topology impact,
  environment variables/secrets, data migration and rollback plan, monitoring
  and alert signals, backup/restore implications, release checks, and any manual
  operator steps needed before real production use.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
