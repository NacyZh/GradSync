import { expect, test, type Page } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

const REQUIRED_LAYOUT_VIEWPORTS = [
  { width: 1440, height: 920, label: 'desktop-1440' },
  { width: 1024, height: 900, label: 'tablet-1024' },
  { width: 768, height: 900, label: 'narrow-tablet-768' },
  { width: 390, height: 844, label: 'mobile-390' },
];
const paperRowSelector = '[data-testid="paper-result-row"]';
const paperRowTitleSelector = '[data-testid="paper-row-title"]';
const selectedTitleSelector = '[data-testid="paper-detail-title"]';
const previewStateSelector = '[data-testid="paper-preview-state"]';
const primaryActionGroupSelector = '[data-testid="paper-primary-action-group"]';

const longLayoutTitle =
  'A Very Long Academic Paper Title About Compact Shared Library Browsing Rows Metadata Density Responsive Containers and Full Detail Context Preservation';
const longLayoutAuthors = [
  'Alexandra Cassandra Researcher',
  'Benjamin Longform Contributor',
  'Charlotte Metadata Specialist',
  'Deepak Responsive Layout Analyst',
];

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
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="Graph Neural Methods for Research Groups.pdf"',
        },
        body: Buffer.from('%PDF-1.4 viewport-download'),
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

async function mockLayoutValidationApi(page: Page, options: { empty?: boolean; error?: number; maintainer?: boolean } = {}) {
  await mockAuthenticatedApi(page);
  const papers = [
    {
      id: 'long-layout',
      projectId: '99',
      title: 'Local PDF Title',
      canonicalTitle: longLayoutTitle,
      authors: longLayoutAuthors,
      publicationYear: 2026,
      venue: 'Proceedings of the International Symposium on Extremely Long Journal Names and Responsive Research Operations',
      keywords: ['layout', 'overflow', 'responsive'],
      titleSource: 'first_page_visible_text',
      visibility: 'group_wide',
      status: 'active',
      downloadAvailable: true,
      viewerAvailable: true,
      actionCapabilities: {
        canRename: Boolean(options.maintainer),
        canDelete: Boolean(options.maintainer),
        canDownload: true,
        canView: true,
      },
      defaultDownloadFilename: `${longLayoutTitle}.pdf`,
    },
    ...Array.from({ length: 12 }, (_, index) => ({
      id: `layout-${index + 1}`,
      projectId: '99',
      title: `Compact Layout Paper ${index + 1}`,
      canonicalTitle: `Compact Layout Paper ${index + 1}`,
      authors: index === 0 ? [] : [`Author ${index + 1}`],
      publicationYear: index === 0 ? undefined : 2026,
      keywords: ['layout'],
      titleSource: index === 0 ? '' : 'embedded_metadata',
      visibility: 'group_wide',
      status: index === 1 ? 'deleted' : 'active',
      downloadAvailable: index !== 1,
      viewerAvailable: index !== 1,
      actionCapabilities: {
        canRename: false,
        canDelete: false,
        canDownload: index !== 1,
        canView: index !== 1,
      },
      defaultDownloadFilename: `Compact Layout Paper ${index + 1}.pdf`,
    })),
  ];

  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith('/api/library/papers/upload-policy/')) {
      await fulfillJson(route, {
        category: 'paper',
        maxSizeBytes: 25 * 1024 * 1024,
        displayLabel: '25 MB',
        allowedExtensions: ['.pdf'],
        contentTypes: ['application/pdf'],
      });
      return;
    }
    if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
      await fulfillJson(route, {
        id: 'import-layout-responsive',
        status: 'accepted',
        requestedBy: 10,
        userMessage: 'Paper imported',
        acceptedPaper: {
          id: 'imported-responsive',
          projectId: '99',
          title: 'Imported Responsive Layout Paper',
          canonicalTitle: 'Imported Responsive Layout Paper',
          authors: [],
          keywords: [],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          viewerAvailable: true,
          defaultDownloadFilename: 'Imported Responsive Layout Paper.pdf',
        },
        duplicatePaper: null,
      }, 202);
      return;
    }
    if (url.endsWith('/api/library/papers/long-layout/download/')) {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': `attachment; filename="${longLayoutTitle}.pdf"`,
        },
        body: Buffer.from('%PDF-1.4 layout'),
      });
      return;
    }
    if (options.error) {
      await fulfillJson(route, { message: 'Layout state permission or service error.' }, options.error);
      return;
    }
    const detail = papers.find((paper) => url.endsWith(`/api/library/papers/${paper.id}/`));
    if (detail) {
      await fulfillJson(route, detail);
      return;
    }
    await fulfillJson(route, { count: options.empty ? 0 : papers.length, results: options.empty ? [] : papers });
  });
}

async function selectPaperRow(page: Page, title: string) {
  await page.getByRole('button', { name: new RegExp(`Open paper ${title}`) }).click();
}

function selectedDetailTitle(page: Page) {
  return page.getByRole('region', { name: 'Selected paper details' }).locator(selectedTitleSelector);
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

async function mockUploadSizePolicyApi(page: Page) {
  await mockAuthenticatedApi(page);
  let importCount = 0;

  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();

    if (url.endsWith('/api/library/papers/upload-policy/')) {
      await fulfillJson(route, {
        category: 'paper',
        maxSizeBytes: 2048,
        displayLabel: '2 KB',
        allowedExtensions: ['.pdf'],
        contentTypes: ['application/pdf'],
      });
      return;
    }

    if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
      importCount += 1;
      if (importCount === 1) {
        await fulfillJson(route, {
          id: 'import-boundary',
          status: 'accepted',
          requestedBy: 10,
          userMessage: 'Paper imported',
          acceptedPaper: {
            id: 'boundary-1',
            projectId: '99',
            title: 'Boundary Upload Paper',
            canonicalTitle: 'Boundary Upload Paper',
            authors: [],
            keywords: [],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
            defaultDownloadFilename: 'Boundary Upload Paper.pdf',
          },
          duplicatePaper: null,
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: 'Boundary Upload Paper',
            confidence: 'high',
            failureReason: '',
          },
          duplicateDetection: null,
          failureReason: '',
        }, 202);
        return;
      }
      await fulfillJson(route, {
        code: 'invalid_upload',
        message: 'The selected PDF exceeds the 2 KB upload size limit.',
        reason: 'oversized',
      }, 400);
      return;
    }

    await fulfillJson(route, { count: 0, results: [] });
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

async function expectNoFullPageHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(overflow.scrollWidth, JSON.stringify(overflow)).toBeLessThanOrEqual(overflow.clientWidth + 1);
  expect(overflow.bodyScrollWidth, JSON.stringify(overflow)).toBeLessThanOrEqual(overflow.innerWidth + 1);
}

async function expectRowsInsideParentBounds(page: Page) {
  const issues = await page.evaluate(({ rowSelector }) => {
    const list = document.querySelector('[data-testid="paper-results-list"]');
    const parentRect = list?.getBoundingClientRect();
    if (!parentRect) return ['missing paper-results-list'];
    return Array.from(document.querySelectorAll(rowSelector)).flatMap((element, index) => {
      const rect = element.getBoundingClientRect();
      const rowIssues: string[] = [];
      if (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1) {
        rowIssues.push(`row ${index} outside parent ${rect.left}-${rect.right}/${parentRect.left}-${parentRect.right}`);
      }
      if ((element as HTMLElement).scrollWidth > (element as HTMLElement).clientWidth + 2) {
        rowIssues.push(`row ${index} has internal horizontal overflow`);
      }
      return rowIssues;
    });
  }, { rowSelector: paperRowSelector });
  expect(issues).toEqual([]);
}

async function expectPrimaryActionsInsideParentBounds(page: Page) {
  const issues = await page.evaluate(({ actionSelector }) => {
    return Array.from(document.querySelectorAll(actionSelector)).flatMap((element, index) => {
      const rect = element.getBoundingClientRect();
      const parentRect = element.parentElement?.getBoundingClientRect();
      if (!parentRect) return [`action group ${index} missing parent`];
      const actionIssues: string[] = [];
      if (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1) {
        actionIssues.push(`action group ${index} outside parent`);
      }
      if ((element as HTMLElement).scrollWidth > (element as HTMLElement).clientWidth + 2) {
        actionIssues.push(`action group ${index} overflow`);
      }
      return actionIssues;
    });
  }, { actionSelector: primaryActionGroupSelector });
  expect(issues).toEqual([]);
}

async function expectPaperLayoutStable(page: Page) {
  await expectNoFullPageHorizontalScroll(page);
  await expectRowsInsideParentBounds(page);
  await expectPrimaryActionsInsideParentBounds(page);
  await expectNoControlOverflow(page);
}

test('paper layout uses compact rows and full selected detail at 1440px', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked layout coverage uses deterministic long-content fixtures.');

  await page.setViewportSize({ width: 1440, height: 920 });
  await mockLayoutValidationApi(page, { maintainer: true });
  await page.goto('/library/papers');

  const longRow = page.getByTestId('paper-result-row').filter({ hasText: 'A Very Long Academic Paper Title' });
  await expect(longRow).toBeVisible();
  await expect(longRow.locator(paperRowTitleSelector)).toHaveClass(/line-clamp-2/);
  await longRow.click();

  await expect(selectedDetailTitle(page)).toContainText(longLayoutTitle);
  await expect(page.getByRole('region', { name: 'Selected paper details' })).toContainText(
    'Proceedings of the International Symposium',
  );
  await expectPaperLayoutStable(page);
});

test('paper selected context, preview, download, and maintainer actions stay bounded at 1024px', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked layout coverage uses deterministic maintainer fixtures.');

  await page.setViewportSize({ width: 1024, height: 900 });
  await mockLayoutValidationApi(page, { maintainer: true });
  await page.goto('/library/papers');

  await page.getByTestId('paper-result-row').filter({ hasText: 'A Very Long Academic Paper Title' }).click();
  await expect(selectedDetailTitle(page)).toContainText(longLayoutTitle);
  await expect(page.locator(previewStateSelector)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Rename paper' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Delete paper' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Download A Very Long Academic Paper Title/ })).toBeVisible();
  await expectPaperLayoutStable(page);
});

test('paper layout viewport matrix has no page, row, or action overflow', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked viewport coverage uses deterministic long-content fixtures.');

  for (const viewport of REQUIRED_LAYOUT_VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await mockLayoutValidationApi(page, { maintainer: true });
    await page.goto('/library/papers');

    await expect(page.getByTestId('paper-result-row').first()).toBeVisible();
    await page.getByTestId('paper-result-row').filter({ hasText: 'A Very Long Academic Paper Title' }).click();
    await expect(selectedDetailTitle(page)).toContainText(longLayoutTitle);
    await expectPaperLayoutStable(page);
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  }
});

test('mobile paper workflow keeps search browse select open upload and download reachable', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked mobile workflow coverage uses deterministic layout fixtures.');

  await page.setViewportSize({ width: 390, height: 844 });
  await mockLayoutValidationApi(page);
  await page.goto('/library/papers');

  await page.getByPlaceholder('Search title, author, year, keyword').fill('Very Long');
  await page.getByTestId('paper-result-row').filter({ hasText: 'A Very Long Academic Paper Title' }).click();
  await expect(selectedDetailTitle(page)).toContainText(longLayoutTitle);
  await expect(page.locator(previewStateSelector)).toBeVisible();
  await page.getByRole('button', { name: /Download A Very Long Academic Paper Title/ }).click();
  await expect(page.getByRole('status')).toContainText('.pdf');

  await page.getByLabel('PDF file').setInputFiles({
    name: 'mobile-clear.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 mobile clear'),
  });
  await expect(page.getByRole('button', { name: 'Clear selected PDFs' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear selected PDFs' }).click();
  await expect(page.getByText('Selected PDF: mobile-clear.pdf')).toHaveCount(0);

  await page.getByLabel('PDF file').setInputFiles({
    name: 'mobile-layout.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 mobile layout'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Accepted: Imported Responsive Layout Paper' }).first()).toBeVisible();
  await expectPaperLayoutStable(page);
});

test('paper layout state coverage stays bounded for empty error permission unavailable and selected states', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked layout state coverage uses deterministic state fixtures.');

  await page.setViewportSize({ width: 768, height: 900 });

  await mockLayoutValidationApi(page, { empty: true });
  await page.goto('/library/papers');
  await expect(page.getByTestId('paper-layout-state')).toContainText('No shared papers');
  await expectNoFullPageHorizontalScroll(page);
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  await mockLayoutValidationApi(page, { error: 500 });
  await page.goto('/library/papers');
  await expect(page.getByTestId('paper-layout-state')).toContainText('Paper library unavailable');
  await expectNoFullPageHorizontalScroll(page);
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  await mockLayoutValidationApi(page, { error: 403 });
  await page.goto('/library/papers');
  await expect(page.getByTestId('paper-layout-state')).toContainText('Layout state permission');
  await expectNoFullPageHorizontalScroll(page);
  await page.unrouteAll({ behavior: 'ignoreErrors' });

  await mockLayoutValidationApi(page);
  await page.goto('/library/papers');
  await page.getByTestId('paper-result-row').filter({ hasText: 'Compact Layout Paper 2' }).click();
  await expect(page.locator(previewStateSelector)).toContainText('This paper is unavailable');
  await page.getByTestId('paper-result-row').filter({ hasText: 'A Very Long Academic Paper Title' }).click();
  await expect(selectedDetailTitle(page)).toContainText(longLayoutTitle);
  await expect(page.getByRole('button', { name: 'Rename paper' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete paper' })).toHaveCount(0);
  await expectPaperLayoutStable(page);
});

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

test('paper upload size guidance uses backend policy and repeats it on rejection', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked upload-size coverage uses deterministic policy fixtures.');

  await page.setViewportSize({ width: 1280, height: 900 });
  await mockUploadSizePolicyApi(page);
  await page.goto('/library/papers');

  await expect(page.getByText('.pdf up to 2 KB')).toBeVisible();
  await expect(page.getByText('.pdf up to 25 MB')).toHaveCount(0);

  await page.getByLabel('PDF file').setInputFiles({
    name: 'boundary.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.alloc(2048, '%'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Accepted: Boundary Upload Paper' }).first()).toBeVisible();

  await page.getByLabel('PDF file').setInputFiles({
    name: 'too-large.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.alloc(2049, '%'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(
    page.getByRole('status').filter({ hasText: 'The selected PDF exceeds the 2 KB upload size limit.' }).first(),
  ).toBeVisible();
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
    await expect(page.getByRole('status').filter({ hasText: 'Accepted: Responsive Reference Systems' }).first()).toBeVisible();
    await expect(page.getByRole('region', { name: 'Selected paper download' })).toContainText('Responsive Reference Systems');
    await expectNoControlOverflow(page);
  });
}

test('shared paper download starts a local PDF download with title-based filename', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked download interception verifies browser filename deterministically.');

  await mockPaperLibraryViewportApi(page);
  await page.goto('/library/papers');

  await page.getByRole('button', { name: /Select paper Graph Neural Methods/ }).click();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /Download Graph Neural Methods/ }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe('Graph Neural Methods for Research Groups.pdf');
});

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
        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'attachment; filename="Graph Neural Methods for Research Groups.pdf"',
          },
          body: Buffer.from('%PDF-1.4 shared-download'),
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
    await expect(page.getByRole('status').filter({ hasText: 'Accepted: Extracted Local PDF Title' }).first()).toBeVisible();
    await page.getByPlaceholder('Search title, author, year, keyword').fill('Extracted');
    await expect(page.getByRole('button', { name: /Select paper Extracted Local PDF Title/ })).toBeVisible();

    await page.getByLabel('PDF file').setInputFiles({
      name: 'renamed.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 duplicate'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Duplicate: Graph Neural Methods for Research Groups' }).first()).toBeVisible();
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
    await expect(page.getByRole('status').filter({ hasText: 'Duplicate: Graph Neural Methods for Research Groups' }).first()).toBeVisible();

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
    await expect(page.getByRole('status').filter({ hasText: 'Accepted: Graph Neural Method for Research Group Distinct' }).first()).toBeVisible();
  }
});
