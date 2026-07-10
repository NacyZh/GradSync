import { expect, type Page, type Route } from '@playwright/test';

export const fullStackE2E = process.env.GRADSYNC_E2E_MODE === 'fullstack';

export function validPdfBuffer(title: string) {
  const escapedTitle = title.replace(/[\\()]/g, (match) => `\\${match}`);
  const pageContent = `BT 72 720 Td (${escapedTitle}) Tj ET\n`;
  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n',
    `4 0 obj\n<< /Length ${Buffer.byteLength(pageContent, 'latin1')} >>\nstream\n${pageContent}endstream\nendobj\n`,
    `5 0 obj\n<< /Title (${escapedTitle}) /Author (GradSync E2E) >>\nendobj\n`,
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  for (const object of objects) {
    offsets.push(Buffer.byteLength(pdf, 'latin1'));
    pdf += object;
  }
  const xrefOffset = Buffer.byteLength(pdf, 'latin1');
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += '0000000000 65535 f \n';
  for (const offset of offsets.slice(1)) {
    pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R /Info 5 0 R >>\n`;
  pdf += `startxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(pdf, 'latin1');
}

export const currentUser = {
  id: 10,
  email: 'advisor@example.edu',
  name: 'Advisor One',
  global_role: 'advisor',
  status: 'active',
};

export const selectedProject = {
  id: 1,
  title: 'Graphene Lab',
  description: 'Research operations validation',
  status: 'active',
  memberships: [],
  current_tasks: [{
    id: 11,
    title: 'Analyze sample',
    status: 'in_progress',
    priority: 'high',
    deadline_at: '2026-06-30T08:00:00Z',
    assignee_id: 12,
    children: [{ id: 12, title: 'Draft chart', status: 'not_started', priority: 'high', assignee_id: 12 }],
  }],
  pending_reviews: [{ target_type: 'progress_report', target_id: '21', submitted_at: '2026-06-20T00:00:00Z' }],
  upcoming_bookings: [{ id: 31, resourceItemId: 41, starts_at: '2026-06-27T08:00:00Z', ends_at: '2026-06-27T09:00:00Z', status: 'reserved' }],
  activity: [
    { source: 'comment', event_type: 'inline_comment.open', summary: 'Comment on progress_report 21: summary', created_at: '2026-06-25T08:00:00Z' },
    { source: 'notification', event_type: 'notification.queued', summary: 'Pending review reminder', created_at: '2026-06-25T08:05:00Z' },
  ],
};

export const codeUploadPolicy = {
  category: 'code',
  maxSizeBytes: 100 * 1024 * 1024,
  displayLabel: '100 MB',
  allowedExtensions: ['.7z', '.bz2', '.gz', '.tar', '.tgz', '.xz', '.zip'],
  contentTypes: ['application/zip', 'application/gzip', 'application/x-gzip', 'application/x-tar', 'application/octet-stream'],
};

export const paperLibraryFixtures = {
  activeUser: currentUser,
  inactiveUser: {
    ...currentUser,
    id: 99,
    email: 'inactive@example.edu',
    status: 'suspended',
  },
  sharedPaper: {
    id: 'paper-1',
    canonical_title: 'Graph Neural Methods for Research Groups',
    title: 'Graph Neural Methods for Research Groups',
    authors: ['Ada Lovelace', 'Grace Hopper'],
    publication_year: 2026,
    keywords: ['graph', 'collaboration'],
    status: 'active',
    title_source: 'embedded_metadata',
    download_available: true,
    default_download_filename: 'Graph Neural Methods for Research Groups.pdf',
    created_at: '2026-07-06T00:00:00Z',
  },
  acceptedImport: {
    id: 'import-accepted',
    status: 'accepted',
    requested_by: currentUser.id,
    user_message: 'Paper imported',
    accepted_paper: null,
    duplicate_paper: null,
    extraction: {
      source: 'embedded_metadata',
      extracted_title: 'Graph Neural Methods for Research Groups',
      confidence: 'high',
      failure_reason: null,
    },
    duplicate_detection: {
      decision: 'accepted_new',
      match_basis: 'none',
      candidate_paper_id: null,
      similarity_score: null,
      review_status: 'none',
    },
    failure_reason: null,
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:02Z',
    completed_at: '2026-07-06T00:00:02Z',
  },
  duplicateImport: {
    id: 'import-duplicate',
    status: 'duplicate',
    requested_by: currentUser.id,
    user_message: 'Duplicate paper detected',
    accepted_paper: null,
    duplicate_paper: null,
    duplicate_detection: {
      decision: 'duplicate_file_fingerprint',
      match_basis: 'file_fingerprint',
      candidate_paper_id: 'paper-1',
      similarity_score: 1,
      review_status: 'none',
    },
    failure_reason: 'duplicate',
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:02Z',
    completed_at: '2026-07-06T00:00:02Z',
  },
  maintainerReviewImport: {
    id: 'import-review',
    status: 'maintainer_review',
    requested_by: currentUser.id,
    user_message: 'Similar paper requires maintainer review',
    accepted_paper: null,
    duplicate_paper: null,
    duplicate_detection: {
      decision: 'maintainer_review',
      match_basis: 'fuzzy_title_metadata',
      candidate_paper_id: 'paper-1',
      similarity_score: 0.86,
      review_status: 'pending',
    },
    failure_reason: null,
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:02Z',
    completed_at: null,
  },
  rejectedImport: {
    id: 'import-rejected',
    status: 'rejected',
    requested_by: currentUser.id,
    user_message: 'Missing reliable title',
    accepted_paper: null,
    duplicate_paper: null,
    extraction: {
      source: 'embedded_metadata',
      extracted_title: null,
      confidence: 'failed',
      failure_reason: 'missing_title',
    },
    duplicate_detection: null,
    failure_reason: 'missing_reliable_title',
    created_at: '2026-07-06T00:00:00Z',
    updated_at: '2026-07-06T00:00:02Z',
    completed_at: '2026-07-06T00:00:02Z',
  },
};

export type DocumentActionCapabilitiesFixture = {
  canView: boolean;
  canDownload: boolean;
  canRename: boolean;
  canDelete: boolean;
  canUploadGroupWide: boolean;
};

export const maintainerDocumentCapabilities: DocumentActionCapabilitiesFixture = {
  canView: true,
  canDownload: true,
  canRename: true,
  canDelete: true,
  canUploadGroupWide: true,
};

export const nonMaintainerDocumentCapabilities: DocumentActionCapabilitiesFixture = {
  canView: true,
  canDownload: true,
  canRename: false,
  canDelete: false,
  canUploadGroupWide: false,
};

export function buildDocumentCategory(overrides: Record<string, unknown> = {}) {
  return {
    id: '1',
    name: 'Protocols',
    description: 'Lab protocols',
    status: 'active',
    createdById: '10',
    ...overrides,
  };
}

export function buildDocumentRecord(overrides: Record<string, unknown> = {}) {
  return {
    id: '4',
    projectId: '1',
    categoryId: '1',
    categoryName: 'Protocols',
    title: 'Microscope Protocol',
    description: 'Calibration workflow',
    visibility: 'group_wide',
    uploaderId: '10',
    documentFileId: '44',
    checksumSha256: 'a'.repeat(64),
    createdAt: '2026-07-03T08:00:00Z',
    status: 'active',
    actionCapabilities: maintainerDocumentCapabilities,
    ...overrides,
  };
}

export function buildLongDocumentRecord(overrides: Record<string, unknown> = {}) {
  return buildDocumentRecord({
    id: 'long-document',
    title:
      'Document title with exceptionally long protocol naming for responsive layout validation',
    description: 'Long document description '.repeat(24),
    categoryName: 'Very long methods and laboratory safety category',
    ...overrides,
  });
}

export async function mockUnauthenticated(page: Page) {
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ status: 401, json: { message: 'Authentication required' } });
  });
}

export async function mockLogin(page: Page, user = currentUser) {
  await page.route('**/api/accounts/login/', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ json: user });
      return;
    }
    await route.fulfill({ status: 405 });
  });
  await page.route('**/api/accounts/logout/', async (route) => {
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/accounts/locale/', async (route) => {
    await route.fulfill({ json: { locale: 'en' } });
  });
  // After login, /api/accounts/me/ returns the authenticated user.
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ json: user });
  });
}

export async function mockAuthenticatedApi(page: Page) {
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ json: currentUser });
  });
  await page.route('**/api/accounts/logout/', async (route) => {
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/accounts/locale/', async (route) => {
    if (route.request().method() === 'PUT') {
      await fulfillJson(route, { locale: 'en' });
      return;
    }
    await fulfillJson(route, { locale: 'en' });
  });
  await page.route('**/api/code-artifacts/upload-policy/', async (route) => {
    await fulfillJson(route, codeUploadPolicy);
  });
  await page.route('**/api/projects/1/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: selectedProject });
      return;
    }
    await route.fulfill({ json: selectedProject });
  });
  await page.route('**/api/projects/1/notifications/', async (route) => {
    await route.fulfill({
      json: {
        results: [{ id: 1, event_type: 'pending_review', target_type: 'progress_report', target_id: '21', subject: 'Pending review reminder', action_path: '/projects/1/reviews', status: 'queued', eligible_at: '2026-06-25T08:05:00Z' }],
      },
    });
  });
  await page.route('**/api/projects/1/tasks/11/', async (route) => {
    await fulfillJson(route, { id: 11, title: 'Analyze sample', status: 'completed', priority: 'high' });
  });
  await page.route('**/api/projects/1/tasks/12/', async (route) => {
    await fulfillJson(route, { id: 12, title: 'Draft chart', status: 'completed', priority: 'high' });
  });
  await page.route('**/api/projects/1/tasks/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 12, title: 'New task', status: 'not_started', priority: 'normal' }, 201);
      return;
    }
    await fulfillJson(route, { results: selectedProject.current_tasks });
  });
}

export async function fulfillJson(route: Route, json: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
}

export async function loginAs(
  page: Page,
  email = 'advisor@example.edu',
  password = 'password123',
) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes('/api/accounts/login/') && response.status() === 200,
    ),
    page.getByRole('button', { name: 'Sign in' }).click(),
  ]);
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
}
