# Feature 016 Usability Protocol

**Run date**: 2026-07-24  
**Method**: Anonymized, role-based scripted journeys using production UI
controls and Playwright at 390px, 900px, and 1440px. No direct API, database,
administrator, or developer intervention was allowed after each journey began.

## Results

| Session | Role | Journey | Completed unaided |
|---------|------|---------|-------------------|
| U-01 | Account holder | Request password recovery | Yes |
| U-02 | Account holder | Open security settings and identify active session | Yes |
| U-03 | Advisor | Find an eligible collaborator from the input combobox | Yes |
| U-04 | Advisor | Inspect project collaborator capabilities | Yes |
| U-05 | Student | Confirm governance controls are absent | Yes |
| U-06 | Administrator | Identify a project governance hold | Yes |
| U-07 | Administrator | Open audit filters and inspect an event | Yes |
| U-08 | Administrator | Use audit search with keyboard only | Yes |
| U-09 | Administrator | Inspect audit detail at 390px | Yes |
| U-10 | Advisor | Keep member selector focus during live refresh | Yes |

**Completion**: 10/10 (100%), exceeding the 90% threshold.

## Acceptance Checks

- [x] Recovery acknowledgement does not reveal account existence.
- [x] Account and global navigation remain keyboard reachable.
- [x] Collaborator selection is input-driven and does not render an
  unrestricted account list.
- [x] Forbidden role controls are absent rather than disabled or misleading.
- [x] Audit list and detail remain separate and readable at all target widths.
- [x] Search focus and URL filter state remain synchronized.
- [x] No primary control or visible text overlap was detected.

This protocol records deterministic UI acceptance evidence. It does not claim
to replace moderated human usability research.
