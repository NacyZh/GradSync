import { expect, test, type Page } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

async function mockCollaborationPages(page: Page) {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/document-categories**', async (route) => fulfillJson(route, [{ id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' }]));
  await page.route('**/api/projects/1/papers/**', async (route) => fulfillJson(route, { results: [{ id: '1', projectId: '1', title: 'Group Wide Graph Paper', authors: ['Lin Chen'], publicationYear: 2025, visibility: 'group_wide', status: 'active', attachments: [{ id: '11', filename: 'graph.pdf', checksumSha256: 'a'.repeat(64), status: 'active' }] }] }));
  await page.route('**/api/projects/1/code-artifacts/**', async (route) => fulfillJson(route, { results: [{ id: '3', projectId: '1', name: 'Group Code Archive', description: 'Microscopy analysis archive', tags: ['analysis'], visibility: 'group_wide', checksumSha256: 'c'.repeat(64), archiveFileId: '9', status: 'active' }] }));
  await page.route('**/api/projects/1/documents**', async (route) => fulfillJson(route, { results: [{ id: '4', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: 'Microscope Protocol', description: 'Calibration workflow', visibility: 'group_wide', uploaderId: '10', checksumSha256: 'a'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }] }));
  await page.route('**/api/projects/1/writing-projects/**', async (route) => fulfillJson(route, { results: [{ id: '2', projectId: '1', studentId: '5', title: 'Thesis Chapter', writingType: 'thesis', status: 'active', versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, draftFileName: 'chapter.docx', fileKind: 'word', status: 'feedback_available', feedback: [] }] }] }));
  await page.route('**/api/resources/', async (route) => fulfillJson(route, { results: [{ id: 7, name: 'Confocal microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.', useSubmissions: [] }] }));
  await page.route('**/api/resource-items/', async (route) => fulfillJson(route, { results: [{ id: 41, resourceTypeId: 1, name: 'Confocal microscope', status: 'available', available: true }] }));
  await page.route('**/api/resource-types/', async (route) => fulfillJson(route, { results: [{ id: 1, name: 'Microscope', scope: 'global', fieldSchema: [], status: 'active' }] }));
  await page.route('**/api/projects/1/bookings/', async (route) => fulfillJson(route, { results: [] }));
}

async function expectNoLayoutOverflow(page: Page) {
  const issues = await page.evaluate(() => {
    const overflow: string[] = [];
    if (document.documentElement.scrollWidth > window.innerWidth + 1) {
      overflow.push(`document overflow ${document.documentElement.scrollWidth}/${window.innerWidth}`);
    }
    for (const element of Array.from(document.querySelectorAll('button, a, input, select, textarea, [role="button"]'))) {
      const html = element as HTMLElement;
      const rect = html.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0 || rect.bottom < 0 || rect.top > window.innerHeight) continue;
      if (html.scrollWidth > html.clientWidth + 2) {
        overflow.push(`${html.tagName.toLowerCase()} text overflow: ${html.textContent?.trim() || html.getAttribute('aria-label') || html.getAttribute('name') || 'control'}`);
      }
    }
    return overflow;
  });
  expect(issues).toEqual([]);
}

async function mockPaperLibraryAccessibility(page: Page) {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
      await fulfillJson(route, {
        id: 'import-a11y',
        status: 'rejected',
        requestedBy: 10,
        userMessage: 'Missing reliable title',
        acceptedPaper: null,
        duplicatePaper: null,
        extraction: {
          source: 'embedded_metadata',
          extractedTitle: '',
          confidence: 'failed',
          failureReason: 'missing_title',
        },
        duplicateDetection: null,
        failureReason: 'missing_reliable_title',
        createdAt: '2026-07-06T00:00:00Z',
        updatedAt: '2026-07-06T00:00:02Z',
        completedAt: '2026-07-06T00:00:02Z',
      }, 202);
      return;
    }
    if (url.endsWith('/api/library/papers/1/download/')) {
      await fulfillJson(route, {
        filename: 'Accessible Paper Workspace.pdf',
        deliveryMode: 'direct_response',
      });
      return;
    }
    if (url.endsWith('/api/library/papers/1/')) {
      await fulfillJson(route, {
        id: '1',
        projectId: '99',
        title: 'Accessible Paper Workspace',
        canonicalTitle: 'Accessible Paper Workspace',
        authors: ['Ada Lovelace'],
        publicationYear: 2026,
        keywords: ['accessibility'],
        visibility: 'group_wide',
        status: 'active',
        downloadAvailable: true,
        defaultDownloadFilename: 'Accessible Paper Workspace.pdf',
      });
      return;
    }
    await fulfillJson(route, {
      count: 1,
      results: [
        {
          id: '1',
          projectId: '99',
          title: 'Accessible Paper Workspace',
          canonicalTitle: 'Accessible Paper Workspace',
          authors: ['Ada Lovelace'],
          publicationYear: 2026,
          keywords: ['accessibility'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Accessible Paper Workspace.pdf',
        },
      ],
    });
  });
}

test('paper library controls are keyboard reachable and announce import and download states', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked accessibility coverage uses deterministic import fixtures.');

  await page.setViewportSize({ width: 390, height: 844 });
  await mockPaperLibraryAccessibility(page);
  await page.goto('/library/papers');

  await expect(page.getByRole('main')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Choose PDFs' })).toBeVisible();
  await expect(page.getByPlaceholder('Search title, author, year, keyword')).toBeVisible();
  await expect(page.getByLabel('Author filter')).toBeVisible();
  await expect(page.getByRole('button', { name: /Select paper Accessible Paper Workspace/ })).toBeVisible();

  await page.keyboard.press('Tab');
  await expect(page.locator(':focus-visible').first()).toBeVisible();

  await page.getByRole('button', { name: /Select paper Accessible Paper Workspace/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('region', { name: 'Selected paper download' })).toContainText('Accessible Paper Workspace');
  await page.getByRole('button', { name: /Download Accessible Paper Workspace/ }).click();
  await expect(page.getByRole('status')).toContainText('Accessible Paper Workspace.pdf');

  await page.getByLabel('PDF file').setInputFiles({
    name: 'missing-title.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 missing title'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Rejected: missing_reliable_title' })).toBeVisible();
  await expectNoLayoutOverflow(page);
});

for (const viewport of [
  { width: 390, height: 844, label: 'mobile' },
  { width: 1280, height: 900, label: 'desktop' },
]) {
  test(`collaboration pages keep landmarks and controls accessible on ${viewport.label}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockCollaborationPages(page);
    if (fullStackE2E) {
      await loginAs(page);
    }
    for (const path of ['/projects/1', '/projects/1/papers', '/projects/1/code', '/projects/1/documents', '/projects/1/writing', '/projects/1/resources']) {
      await page.goto(path);
      await expect(page.getByRole('banner')).toBeVisible();
      await expect(page.getByRole('main')).toBeVisible();
      await expect(page.getByRole('navigation', { name: 'Primary workspace' })).toBeVisible();
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus-visible').first()).toBeVisible();
      await expectNoLayoutOverflow(page);
    }
  });
}
