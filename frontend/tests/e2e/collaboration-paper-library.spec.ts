import { expect, test, type Page } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

async function mockPaperLibraryViewportApi(page: Page) {
  await mockAuthenticatedApi(page);
  let imported = false;

  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();

    if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
      imported = true;
      await fulfillJson(route, {
        id: 'import-layout',
        status: 'accepted',
        requestedBy: 10,
        userMessage: 'Paper imported',
        acceptedPaper: {
          id: '2',
          projectId: '99',
          title: 'Responsive Reference Systems',
          canonicalTitle: 'Responsive Reference Systems',
          authors: [],
          keywords: ['layout'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Responsive Reference Systems.pdf',
        },
        duplicatePaper: null,
        extraction: {
          source: 'embedded_metadata',
          extractedTitle: 'Responsive Reference Systems',
          confidence: 'high',
          failureReason: '',
        },
        duplicateDetection: null,
        failureReason: '',
        createdAt: '2026-07-06T00:00:00Z',
        updatedAt: '2026-07-06T00:00:02Z',
        completedAt: '2026-07-06T00:00:02Z',
      }, 202);
      return;
    }

    if (url.endsWith('/api/library/papers/1/download/')) {
      await fulfillJson(route, {
        filename: 'Graph Neural Methods for Research Groups.pdf',
        deliveryMode: 'direct_response',
      });
      return;
    }

    if (url.endsWith('/api/library/papers/1/')) {
      await fulfillJson(route, {
        id: '1',
        projectId: '99',
        title: 'Graph Neural Methods for Research Groups',
        canonicalTitle: 'Graph Neural Methods for Research Groups',
        authors: ['Ada Lovelace', 'Grace Hopper'],
        publicationYear: 2026,
        keywords: ['graph', 'collaboration'],
        visibility: 'group_wide',
        status: 'active',
        downloadAvailable: true,
        defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
      });
      return;
    }

    if (url.endsWith('/api/library/papers/2/')) {
      await fulfillJson(route, {
        id: '2',
        projectId: '99',
        title: 'Responsive Reference Systems',
        canonicalTitle: 'Responsive Reference Systems',
        authors: [],
        keywords: ['layout'],
        visibility: 'group_wide',
        status: 'active',
        downloadAvailable: true,
        defaultDownloadFilename: 'Responsive Reference Systems.pdf',
      });
      return;
    }

    await fulfillJson(route, {
      count: imported ? 2 : 1,
      results: [
        {
          id: '1',
          projectId: '99',
          title: 'Graph Neural Methods for Research Groups',
          canonicalTitle: 'Graph Neural Methods for Research Groups',
          authors: ['Ada Lovelace', 'Grace Hopper'],
          publicationYear: 2026,
          keywords: ['graph', 'collaboration'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
        },
        ...(imported
          ? [
              {
                id: '2',
                projectId: '99',
                title: 'Responsive Reference Systems',
                canonicalTitle: 'Responsive Reference Systems',
                authors: [],
                keywords: ['layout'],
                visibility: 'group_wide',
                status: 'active',
                downloadAvailable: true,
                defaultDownloadFilename: 'Responsive Reference Systems.pdf',
              },
            ]
          : []),
      ],
    });
  });
}

async function expectNoControlOverflow(page: Page) {
  const issues = await page.evaluate(() => {
    const overflow: string[] = [];
    if (document.documentElement.scrollWidth > window.innerWidth + 1) {
      overflow.push(`document overflow ${document.documentElement.scrollWidth}/${window.innerWidth}`);
    }
    for (const element of Array.from(document.querySelectorAll('button, input, select, textarea'))) {
      const html = element as HTMLElement;
      const rect = html.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;
      if (html.scrollWidth > html.clientWidth + 2) {
        overflow.push(html.textContent?.trim() || html.getAttribute('aria-label') || html.tagName.toLowerCase());
      }
    }
    return overflow;
  });
  expect(issues).toEqual([]);
}

for (const viewport of [
  { width: 1280, height: 900, label: 'desktop' },
  { width: 390, height: 844, label: 'narrow' },
]) {
  test(`paper library completes search, import, select, and download on ${viewport.label}`, async ({ page }) => {
    test.skip(fullStackE2E, 'Mocked viewport coverage uses deterministic import fixtures.');

    await page.setViewportSize(viewport);
    await mockPaperLibraryViewportApi(page);
    await page.goto('/library/papers');

    await expect(page.getByRole('region', { name: 'Paper import and download' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Shared paper search and display' })).toBeVisible();
    await expect(page.getByLabel('Paper title')).toHaveCount(0);

    await page.getByPlaceholder('Search title, author, year, keyword').fill('Graph');
    await page.getByRole('button', { name: /Select paper Graph Neural Methods/ }).click();
    await expect(page.getByRole('region', { name: 'Selected paper download' })).toContainText('Graph Neural Methods');
    await page.getByRole('button', { name: /Download Graph Neural Methods/ }).click();
    await expect(page.getByRole('status')).toContainText('Graph Neural Methods for Research Groups.pdf');

    await page.getByLabel('PDF file').setInputFiles({
      name: 'local-layout.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 layout'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(page.getByText('Accepted: Responsive Reference Systems')).toBeVisible();
    await expect(page.getByRole('region', { name: 'Selected paper download' })).toContainText('Responsive Reference Systems');
    await expectNoControlOverflow(page);
  });
}

test('shared paper library search and download does not require project membership', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let importCount = 0;
  let imported = false;

  if (!fullStackE2E) {
    await page.route('**/api/library/papers/**', async (route) => {
      const request = route.request();
      const url = request.url();
      if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
        importCount += 1;
        imported = true;
        const responses = [
          {
            id: 'import-accepted',
            status: 'accepted',
            requestedBy: 10,
            userMessage: 'Paper imported',
            acceptedPaper: {
              id: '2',
              projectId: '99',
              title: 'Extracted Local PDF Title',
              canonicalTitle: 'Extracted Local PDF Title',
              authors: [],
              keywords: [],
              visibility: 'group_wide',
              status: 'active',
              downloadAvailable: true,
              defaultDownloadFilename: 'Extracted Local PDF Title.pdf',
            },
            duplicatePaper: null,
            extraction: {
              source: 'embedded_metadata',
              extractedTitle: 'Extracted Local PDF Title',
              confidence: 'high',
              failureReason: '',
            },
            duplicateDetection: null,
            failureReason: '',
            createdAt: '2026-07-06T00:00:00Z',
            updatedAt: '2026-07-06T00:00:02Z',
            completedAt: '2026-07-06T00:00:02Z',
          },
          {
            id: 'import-duplicate',
            status: 'duplicate',
            requestedBy: 10,
            userMessage: 'Duplicate paper detected.',
            acceptedPaper: null,
            duplicatePaper: {
              id: '1',
              projectId: '99',
              title: 'Graph Neural Methods for Research Groups',
              canonicalTitle: 'Graph Neural Methods for Research Groups',
              authors: ['Ada Lovelace', 'Grace Hopper'],
              keywords: ['graph', 'collaboration'],
              visibility: 'group_wide',
              status: 'active',
              downloadAvailable: true,
              defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
            },
            extraction: {
              source: 'embedded_metadata',
              extractedTitle: 'Graph Neural Methods for Research Groups',
              confidence: 'high',
              failureReason: '',
            },
            duplicateDetection: {
              decision: 'duplicate_file_fingerprint',
              matchBasis: 'file_fingerprint',
              candidatePaperId: '1',
              similarityScore: 1,
              reviewStatus: 'none',
            },
            failureReason: 'duplicate',
          },
          {
            id: 'import-review-duplicate',
            status: 'maintainer_review',
            requestedBy: 10,
            userMessage: 'Possible duplicate queued for maintainer review.',
            acceptedPaper: null,
            duplicatePaper: {
              id: '1',
              projectId: '99',
              title: 'Graph Neural Methods for Research Groups',
              canonicalTitle: 'Graph Neural Methods for Research Groups',
              authors: ['Ada Lovelace', 'Grace Hopper'],
              keywords: ['graph', 'collaboration'],
              visibility: 'group_wide',
              status: 'active',
              downloadAvailable: true,
              defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
            },
            extraction: {
              source: 'embedded_metadata',
              extractedTitle: 'Graph Neural Method for Research Group',
              confidence: 'high',
              failureReason: '',
            },
            duplicateDetection: {
              decision: 'maintainer_review',
              matchBasis: 'fuzzy_title_metadata',
              candidatePaperId: '1',
              similarityScore: 0.96,
              reviewStatus: 'pending',
            },
            failureReason: '',
          },
          {
            id: 'import-review-distinct',
            status: 'maintainer_review',
            requestedBy: 10,
            userMessage: 'Possible duplicate queued for maintainer review.',
            acceptedPaper: null,
            duplicatePaper: {
              id: '1',
              projectId: '99',
              title: 'Graph Neural Methods for Research Groups',
              canonicalTitle: 'Graph Neural Methods for Research Groups',
              authors: ['Ada Lovelace', 'Grace Hopper'],
              keywords: ['graph', 'collaboration'],
              visibility: 'group_wide',
              status: 'active',
              downloadAvailable: true,
              defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
            },
            extraction: {
              source: 'embedded_metadata',
              extractedTitle: 'Graph Neural Method for Research Group Distinct',
              confidence: 'high',
              failureReason: '',
            },
            duplicateDetection: {
              decision: 'maintainer_review',
              matchBasis: 'fuzzy_title_metadata',
              candidatePaperId: '1',
              similarityScore: 0.88,
              reviewStatus: 'pending',
            },
            failureReason: '',
          },
        ];
        await fulfillJson(route, responses[Math.min(importCount - 1, responses.length - 1)], 202);
        return;
      }
      if (url.endsWith('/api/library/papers/1/download/')) {
        await fulfillJson(route, {
          filename: 'Graph Neural Methods for Research Groups.pdf',
          deliveryMode: 'direct_response',
        });
        return;
      }
      if (url.endsWith('/api/library/papers/1/')) {
        await fulfillJson(route, {
          id: '1',
          projectId: '99',
          title: 'Graph Neural Methods for Research Groups',
          canonicalTitle: 'Graph Neural Methods for Research Groups',
          authors: ['Ada Lovelace', 'Grace Hopper'],
          publicationYear: 2026,
          keywords: ['graph', 'collaboration'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
        });
        return;
      }
      await fulfillJson(route, {
        count: imported ? 2 : 1,
        results: imported
          ? [
              {
                id: '2',
                projectId: '99',
                title: 'Extracted Local PDF Title',
                canonicalTitle: 'Extracted Local PDF Title',
                authors: [],
                keywords: [],
                visibility: 'group_wide',
                status: 'active',
                downloadAvailable: true,
                defaultDownloadFilename: 'Extracted Local PDF Title.pdf',
              },
            ]
          : [
              {
                id: '1',
                projectId: '99',
                title: 'Graph Neural Methods for Research Groups',
                canonicalTitle: 'Graph Neural Methods for Research Groups',
                authors: ['Ada Lovelace', 'Grace Hopper'],
                publicationYear: 2026,
                keywords: ['graph', 'collaboration'],
                visibility: 'group_wide',
                status: 'active',
                downloadAvailable: true,
                defaultDownloadFilename: 'Graph Neural Methods for Research Groups.pdf',
              },
            ],
      });
    });
    await page.route('**/api/library/paper-imports/**', async (route) => {
      const url = route.request().url();
      if (url.endsWith('/api/library/paper-imports/import-review-duplicate/review/')) {
        await fulfillJson(route, {
          id: 'import-review-duplicate',
          status: 'duplicate',
          requestedBy: 10,
          userMessage: 'Maintainer confirmed this upload duplicates an existing paper.',
          acceptedPaper: null,
          duplicatePaper: {
            id: '1',
            projectId: '99',
            title: 'Graph Neural Methods for Research Groups',
            canonicalTitle: 'Graph Neural Methods for Research Groups',
            authors: ['Ada Lovelace', 'Grace Hopper'],
            keywords: ['graph', 'collaboration'],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          duplicateDetection: {
            decision: 'maintainer_review',
            matchBasis: 'fuzzy_title_metadata',
            candidatePaperId: '1',
            similarityScore: 0.96,
            reviewStatus: 'confirmed_duplicate',
          },
          failureReason: 'duplicate',
        });
        return;
      }
      if (url.endsWith('/api/library/paper-imports/import-review-distinct/review/')) {
        await fulfillJson(route, {
          id: 'import-review-distinct',
          status: 'accepted',
          requestedBy: 10,
          userMessage: 'Maintainer confirmed this upload as a distinct paper.',
          acceptedPaper: {
            id: '3',
            projectId: '99',
            title: 'Graph Neural Method for Research Group Distinct',
            canonicalTitle: 'Graph Neural Method for Research Group Distinct',
            authors: [],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
          },
          duplicatePaper: null,
          duplicateDetection: {
            decision: 'maintainer_review',
            matchBasis: 'fuzzy_title_metadata',
            candidatePaperId: '1',
            similarityScore: 0.88,
            reviewStatus: 'confirmed_distinct',
          },
          failureReason: '',
        });
        return;
      }
      await fulfillJson(route, { message: 'Not found' }, 404);
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
  }

  await page.goto('/library/papers');
  await expect(page.getByRole('heading', { name: 'Paper library' })).toBeVisible();
  await expect(page.getByText(/join a project/i)).toHaveCount(0);
  await page.getByPlaceholder('Search title, author, year, keyword').fill('Graph');
  await expect(page.getByRole('button', { name: /Select paper Graph Neural Methods/ })).toBeVisible();
  await page.getByRole('button', { name: /Select paper Graph Neural Methods/ }).click();
  await page.getByRole('button', { name: /Download/ }).click();
  await expect(page.getByRole('status')).toContainText('Graph Neural Methods');

  if (!fullStackE2E) {
    await expect(page.getByLabel('Paper title')).toHaveCount(0);
    await page.getByLabel('PDF file').setInputFiles({
      name: 'local-name.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(page.getByText('Accepted: Extracted Local PDF Title')).toBeVisible();
    await page.getByPlaceholder('Search title, author, year, keyword').fill('Extracted');
    await expect(page.getByRole('button', { name: /Select paper Extracted Local PDF Title/ })).toBeVisible();

    await page.getByLabel('PDF file').setInputFiles({
      name: 'renamed.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 duplicate'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(page.getByText('Duplicate: Graph Neural Methods for Research Groups')).toBeVisible();
    await expect(page.getByRole('button', { name: 'View existing paper' })).toBeVisible();

    await page.getByLabel('PDF file').setInputFiles({
      name: 'fuzzy.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fuzzy'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(
      page.getByRole('status').filter({ hasText: 'Maintainer review required' }).first(),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Confirm duplicate' }).click();
    await expect(page.getByText('Duplicate: Graph Neural Methods for Research Groups')).toBeVisible();

    await page.getByLabel('PDF file').setInputFiles({
      name: 'fuzzy-distinct.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fuzzy distinct'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(
      page.getByRole('status').filter({ hasText: 'Maintainer review required' }).first(),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Confirm distinct' }).click();
    await expect(page.getByText('Accepted: Graph Neural Method for Research Group Distinct')).toBeVisible();
  }
});
