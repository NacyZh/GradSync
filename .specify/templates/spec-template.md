# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## 1. Business Background, User Roles, and Core Goals *(mandatory)*

<!--
  Required by the GradSync Constitution. Describe why this feature exists, who
  uses it, and which business outcome it must achieve. Avoid implementation
  details here.
-->

**Business Background**: [Problem/opportunity and current pain]

**User Roles**:

- **[Role 1]**: [Responsibilities and permissions relevant to this feature]
- **[Role 2]**: [Responsibilities and permissions relevant to this feature]

**Core Goals**:

- [Goal 1]
- [Goal 2]

## 2. Complete Positive Business Flows *(mandatory)*

<!--
  User stories MUST be independently testable and prioritized by value.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*

<!--
  Include normal error handling, boundary values, degraded dependencies,
  authorization failures, concurrency/race conditions, and unsupported actions.
-->

- [Boundary or exception scenario 1]
- [Boundary or exception scenario 2]
- [Degradation/fallback scenario]

## 4. Quantifiable Acceptance Criteria *(mandatory)*

<!--
  Acceptance criteria MUST be measurable and automatable where possible. These
  AC IDs are referenced by tasks.md.
-->

- **AC-001**: [Measurable acceptance criterion]
- **AC-002**: [Measurable acceptance criterion]
- **AC-003**: [Measurable acceptance criterion]

## 5. Dependencies, Assumptions, and Unsupported Scope *(mandatory)*

### Dependencies and External Systems

- [Dependency or external system]

### Business Assumptions

- [Assumption]

### Included Scope

- [Capability included in this release]

### Unsupported / Out of Scope

- [Capability explicitly not supported in this release]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]

### Security & Privacy Requirements *(include when data, accounts, roles, or integrations are involved)*

- **SEC-001**: System MUST enforce [authorization/isolation rule] for
  [resource/action]
- **SEC-002**: System MUST protect [secret/token/personal data] by [storage,
  transport, masking, retention, or audit rule]
- **SEC-003**: System MUST record auditable events for
  [privileged/security-sensitive action]

### User Experience Requirements *(include for user-facing work)*

- **UX-001**: Experience MUST follow [existing pattern/component/flow] for
  [interaction]
- **UX-002**: Experience MUST provide clear loading, empty, success, warning, and
  error states for [journey]
- **UX-003**: Experience MUST be usable with keyboard navigation and assistive
  labels for [controls/content]

### Performance Requirements *(mandatory when user journeys can be measured)*

- **PERF-001**: [Journey/action] MUST complete within [measurable target]
- **PERF-002**: System MUST handle [scale condition] without
  [degradation threshold]

### Operational Requirements *(mandatory for production-impacting work)*

- **OPS-001**: System MUST expose or preserve
  [health/readiness/metric/log/audit signal] for [operation]
- **OPS-002**: Deployment MUST support
  [migration/rollback/backup/restore/retry behavior] for [change]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Specification Review and Clarifications *(mandatory)*

**Required Reviewers**:

- Product: [name/status]
- Testing: [name/status]
- Development: [name/status]

**Open Questions**:

- [Question or "None"]

**Closed Clarifications**:

- [Decision/date or "None"]
