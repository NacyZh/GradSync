export function registrationPayload(overrides: Partial<Record<string, string>> = {}) {
  return {
    email: 'student@example.com',
    password: 'StrongPass1!',
    nickname: 'Student A',
    requestedRole: 'student',
    degreeType: 'masters',
    ...overrides,
  };
}

export function assetVisibilityFixture(overrides: Partial<Record<string, string | number>> = {}) {
  return {
    id: 1,
    projectId: 1,
    visibility: 'project_members',
    title: 'Shared asset',
    ...overrides,
  };
}

export function writingFixture(overrides: Partial<Record<string, string | number>> = {}) {
  return {
    id: 1,
    title: 'Thesis draft',
    status: 'active',
    versionCount: 1,
    ...overrides,
  };
}

export function resourceFixture(overrides: Partial<Record<string, string | number | null>> = {}) {
  return {
    id: 1,
    name: 'Microscope',
    resourceTypeId: 1,
    resourceType: 'Microscope',
    totalQuantity: 3,
    availableQuantity: 3,
    status: 'active',
    confirmationPolicyOverride: null,
    effectiveConfirmationPolicy: 'immediate',
    version: 1,
    ...overrides,
  };
}

export function resourceConflictFixture(overrides: Partial<Record<string, string | number | boolean>> = {}) {
  return {
    code: 'resource_has_history',
    detail: 'Resource has retained history',
    canRetire: true,
    ...overrides,
  };
}

export function resourceBookingFixture(overrides: Partial<Record<string, string | number | null>> = {}) {
  return {
    id: 1,
    resourceId: 1,
    requestedById: 2,
    startsAt: '2026-07-12T08:00:00Z',
    endsAt: '2026-07-12T09:00:00Z',
    quantity: 1,
    status: 'confirmed',
    confirmationPolicy: 'immediate',
    reviewerId: null,
    version: 1,
    ...overrides,
  };
}

export function notificationFixture(overrides: Partial<Record<string, string | number>> = {}) {
  return {
    id: 1,
    eventType: 'email_verification',
    status: 'queued',
    subject: 'Verify your GradSync email',
    ...overrides,
  };
}
