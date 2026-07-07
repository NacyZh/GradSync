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

async function selectPaperRow(page: Page, title: string) {
  await page.getByRole('button', { name: new RegExp(`Open paper ${title}`) }).click();
}

async function interceptPaperDownload(page: Page, paperId: string, filename: string) {
  await page.route(`**/api/library/papers/${paperId}/download/`, async (route) => {
    await fulfillJson(route, {
      filename,
      deliveryMode: 'direct_response',
    });
  });
}

async function expectEnglishPaperLibraryText(page: Page) {
  await expect(page.getByRole('heading', { name: 'Paper library' })).toBeVisible();
  await expect(page.getByText(/论文|选择文件|下载论文/)).toHaveCount(0);
}

async function mockScrollablePaperLibraryApi(page: Page) {
  await mockAuthenticatedApi(page);
  const papers = Array.from({ length: 16 }, (_, index) => ({
    id: String(index + 1),
    projectId: '99',
    title: `Scrollable Paper ${index + 1}`,
    canonicalTitle: `Scrollable Paper ${index + 1}`,
    authors: [`Author ${index + 1}`],
    publicationYear: 2026,
    keywords: ['scroll'],
    visibility: 'group_wide',
    status: 'active',
    downloadAvailable: true,
    viewerAvailable: true,
    defaultDownloadFilename: `Scrollable Paper ${index + 1}.pdf`,
  }));

  await page.route('**/api/library/papers/**', async (route) => {
    const url = route.request().url();
    const detail = papers.find((paper) => url.endsWith(`/api/library/papers/${paper.id}/`));
    if (detail) {
      await fulfillJson(route, detail);
      return;
    }
    await fulfillJson(route, { count: papers.length, results: papers });
  });
}

async function mockRenamePaperLibraryApi(page: Page) {
  await mockAuthenticatedApi(page);
  let paper = {
    id: 'rename-1',
    projectId: '99',
    title: 'Original Rename Title',
    canonicalTitle: 'Original Rename Title',
    authors: ['Ada Lovelace'],
    publicationYear: 2026,
    keywords: ['rename'],
    visibility: 'group_wide',
    status: 'active',
    downloadAvailable: true,
    viewerAvailable: true,
    actionCapabilities: {
      canRename: true,
      canDelete: false,
      canDownload: true,
      canView: true,
    },
    defaultDownloadFilename: 'Original Rename Title.pdf',
  };

  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith('/api/library/papers/rename-1/') && request.method() === 'PATCH') {
      paper = {
        ...paper,
        title: 'Renamed Playwright Title',
        canonicalTitle: 'Renamed Playwright Title',
        defaultDownloadFilename: 'Renamed Playwright Title.pdf',
      };
      await fulfillJson(route, paper);
      return;
    }
    if (url.endsWith('/api/library/papers/rename-1/')) {
      await fulfillJson(route, paper);
      return;
    }
    await fulfillJson(route, { count: 1, results: [paper] });
  });
}

async function mockDeletePaperLibraryApi(page: Page) {
  await mockAuthenticatedApi(page);
  let papers = [
    {
      id: 'delete-1',
      projectId: '99',
      title: 'Delete Playwright Paper',
      canonicalTitle: 'Delete Playwright Paper',
      authors: ['Ada Lovelace'],
      publicationYear: 2026,
      keywords: ['delete'],
      visibility: 'group_wide',
      status: 'active',
      downloadAvailable: true,
      viewerAvailable: true,
      actionCapabilities: {
        canRename: true,
        canDelete: true,
        canDownload: true,
        canView: true,
      },
      defaultDownloadFilename: 'Delete Playwright Paper.pdf',
    },
  ];

  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith('/api/library/papers/delete-1/') && request.method() === 'DELETE') {
      papers = [];
      await fulfillJson(route, null);
      return;
    }
    const detail = papers.find((paper) => url.endsWith(`/api/library/papers/${paper.id}/`));
    if (detail) {
      await fulfillJson(route, detail);
      return;
    }
    await fulfillJson(route, { count: papers.length, results: papers });
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

test('paper rows scroll, select, and open an in-page viewer with pointer and keyboard', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked viewport coverage uses deterministic scroll fixtures.');

  await page.setViewportSize({ width: 1280, height: 900 });
  await mockScrollablePaperLibraryApi(page);
  await page.goto('/library/papers');

  const list = page.getByTestId('paper-results-list');
  await expect(list).toBeVisible();
  await expect(list).toHaveCSS('overflow-y', 'auto');
  await selectPaperRow(page, 'Scrollable Paper 14');
  await expect(page.getByRole('region', { name: 'Selected paper details' })).toContainText(
    'Scrollable Paper 14',
  );
  await expect(page.getByText('In-page viewer')).toBeVisible();

  await page.getByRole('button', { name: /Open paper Scrollable Paper 2/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('region', { name: 'Selected paper details' })).toContainText(
    'Scrollable Paper 2',
  );
});

test('maintainer renames a selected paper and sees updated list and detail context', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked rename coverage uses deterministic maintainer fixtures.');

  await page.setViewportSize({ width: 1280, height: 900 });
  await mockRenamePaperLibraryApi(page);
  await page.goto('/library/papers');

  await selectPaperRow(page, 'Original Rename Title');
  await page.getByRole('button', { name: 'Rename paper' }).click();
  await page.getByLabel('New paper title').fill('Renamed Playwright Title');
  await page.getByRole('button', { name: 'Save title' }).click();

  await expect(page.getByRole('button', { name: /Open paper Renamed Playwright Title/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Selected paper details' })).toContainText(
    'Renamed Playwright Title',
  );
  await expectNoControlOverflow(page);
});

test('maintainer deletes a selected paper and no restore action appears', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked delete coverage uses deterministic maintainer fixtures.');

  await page.setViewportSize({ width: 1280, height: 900 });
  await mockDeletePaperLibraryApi(page);
  await page.goto('/library/papers');

  await selectPaperRow(page, 'Delete Playwright Paper');
  await page.getByRole('button', { name: 'Delete paper' }).click();
  await page.getByLabel('Delete reason').fill('Duplicate upload');
  await page.getByRole('button', { name: 'Confirm delete' }).click();

  await expect(page.getByRole('button', { name: /Open paper Delete Playwright Paper/ })).toHaveCount(0);
  await expect(page.getByText('No shared papers are available yet.')).toBeVisible();
  await expect(page.getByRole('button', { name: /restore/i })).toHaveCount(0);
  await expectNoControlOverflow(page);
});

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
