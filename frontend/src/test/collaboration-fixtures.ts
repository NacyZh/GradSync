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

export function resourceFixture(overrides: Partial<Record<string, string | number>> = {}) {
  return {
    id: 1,
    name: 'Microscope',
    status: 'available',
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
