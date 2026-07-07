import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('paper import, code download, and locale persistence workflow is reachable', async ({ page }) => {
  if (!fullStackE2E) {
    await page.route('**/api/library/papers/**', async (route) => {
      const request = route.request();
      const url = request.url();
      if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
        await fulfillJson(route, {
          id: 'import-duplicate',
          status: 'duplicate',
          requestedBy: 10,
          userMessage: 'Duplicate paper detected.',
          acceptedPaper: null,
          duplicatePaper: {
            id: '1',
            projectId: '1',
            title: 'Graph Neural Methods',
            canonicalTitle: 'Graph Neural Methods',
            authors: ['Lin Chen'],
            publicationYear: 2026,
            keywords: ['graph'],
            visibility: 'group_wide',
            status: 'active',
            downloadAvailable: true,
            defaultDownloadFilename: 'Graph Neural Methods.pdf',
          },
          extraction: {
            source: 'embedded_metadata',
            extractedTitle: 'Graph Neural Methods',
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
        }, 202);
        return;
      }
      if (url.endsWith('/api/library/papers/1/download/')) {
        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'attachment; filename="Graph Neural Methods.pdf"',
          },
          body: Buffer.from('%PDF-1.4 locale-download'),
        });
        return;
      }
      if (url.endsWith('/api/library/papers/1/')) {
        await fulfillJson(route, {
          id: '1',
          projectId: '1',
          title: 'Graph Neural Methods',
          canonicalTitle: 'Graph Neural Methods',
          authors: ['Lin Chen'],
          publicationYear: 2026,
          keywords: ['graph'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Graph Neural Methods.pdf',
        });
        return;
      }
      await fulfillJson(route, {
        results: [{
          id: '1',
          projectId: '1',
          title: 'Graph Neural Methods',
          canonicalTitle: 'Graph Neural Methods',
          authors: ['Lin Chen'],
          publicationYear: 2026,
          keywords: ['graph'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Graph Neural Methods.pdf',
        }],
        count: 1,
      });
    });
    await page.route('**/api/projects/1/papers/**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback();
        return;
      }
      await fulfillJson(route, {
        results: [{
          id: '1',
          projectId: '1',
          title: 'Graph Neural Methods',
          authors: ['Lin Chen'],
          publicationYear: 2026,
          doi: '10.1000/graph',
          status: 'active',
          attachments: [{ id: '1', filename: 'graph.pdf', checksumSha256: 'a', status: 'active' }],
        }],
      });
    });
    await page.route('**/api/projects/1/papers/imports/', async (route) => {
      await fulfillJson(route, {
        id: 'batch-1',
        projectId: '1',
        status: 'staged',
        totalItems: 1,
        acceptedCount: 0,
        duplicateCount: 1,
        errorCount: 0,
        results: [{ status: 'duplicate', duplicateReason: 'doi', message: 'Duplicate paper detected' }],
      }, 201);
    });
    await page.route('**/api/projects/1/papers/1/download/', async (route) => {
      await fulfillJson(route, { filename: 'graph.pdf', deliveryMode: 'direct_response' });
    });
    await page.route('**/api/projects/1/code-artifacts/**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback();
        return;
      }
      await fulfillJson(route, {
        results: [{
          id: '1',
          projectId: '1',
          name: 'Simulator',
          status: 'active',
          latestVersion: { id: '2', artifactId: '1', projectId: '1', versionLabel: 'v1', filename: 'sim.zip', checksumSha256: 'b', status: 'active' },
        }],
      });
    });
    await page.route('**/api/projects/1/code-artifacts/1/versions/2/download/', async (route) => {
      await fulfillJson(route, { filename: 'sim.zip', deliveryMode: 'direct_response' });
    });
    await page.route('**/api/accounts/locale/', async (route) => {
      if (route.request().method() === 'PUT') {
        await fulfillJson(route, { locale: 'zh' });
        return;
      }
      await fulfillJson(route, { locale: 'en' });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
  }

  await page.goto('/library/papers');
  await expect(page.getByRole('heading', { name: 'Paper library' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Select paper Graph Neural Methods/ })).toBeVisible();
  await expect(page.getByLabel('Paper title')).toHaveCount(0);
  await page.getByLabel('PDF file').setInputFiles({
    name: 'graph-copy.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(
    page
      .locator('#paper-import-status, [role="alert"]')
      .filter({
        hasText:
          /Accepted|Duplicate|Rejected|Failed|Maintainer review|required|corrupted|unreadable|PDF|missing/i,
      })
      .first(),
  ).toBeVisible();
  await page.getByRole('button', { name: /Download Graph Neural Methods/ }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Download started' })).toContainText('Graph Neural Methods.pdf');

  await page.goto('/projects/1/code');
  await expect(page.getByRole('heading', { name: 'Code repository' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Simulator' })).toBeVisible();
  await page.getByRole('button', { name: 'Download' }).click();
  await expect(page.getByRole('status')).toContainText('sim.zip');

  await page.getByRole('button', { name: /Language|语言/ }).click();
});

test('English paper-library upload, rename, delete, viewer, and download states stay English-only', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked English localization coverage uses deterministic paper fixtures.');

  await page.route('**/api/accounts/locale/', async (route) => {
    await fulfillJson(route, { locale: 'en' });
  });

  let paper = {
    id: 'locale-1',
    projectId: '1',
    title: 'Locale Review Paper',
    canonicalTitle: 'Locale Review Paper',
    authors: ['Lin Chen'],
    publicationYear: 2026,
    keywords: ['locale'],
    visibility: 'group_wide',
    status: 'active',
    downloadAvailable: true,
    viewerAvailable: true,
    defaultDownloadFilename: 'Locale Review Paper.pdf',
    actionCapabilities: {
      canRename: true,
      canDelete: true,
      canDownload: true,
      canView: true,
    },
  };
  let deleted = false;

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
      await fulfillJson(route, {
        id: 'locale-import',
        status: 'accepted',
        requestedBy: 10,
        userMessage: 'Paper imported',
        acceptedPaper: {
          ...paper,
          id: 'locale-imported',
          title: 'Imported Locale Paper',
          canonicalTitle: 'Imported Locale Paper',
          defaultDownloadFilename: 'Imported Locale Paper.pdf',
        },
        duplicatePaper: null,
        extraction: {
          source: 'embedded_metadata',
          extractedTitle: 'Imported Locale Paper',
          confidence: 'high',
          failureReason: '',
        },
        duplicateDetection: null,
        failureReason: '',
      }, 202);
      return;
    }

    if (url.endsWith('/api/library/papers/locale-1/download/')) {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="Renamed Locale Paper.pdf"',
        },
        body: Buffer.from('%PDF-1.4 locale-paper'),
      });
      return;
    }

    if (url.endsWith('/api/library/papers/locale-1/') && request.method() === 'PATCH') {
      paper = {
        ...paper,
        title: 'Renamed Locale Paper',
        canonicalTitle: 'Renamed Locale Paper',
        defaultDownloadFilename: 'Renamed Locale Paper.pdf',
      };
      await fulfillJson(route, paper);
      return;
    }

    if (url.endsWith('/api/library/papers/locale-1/') && request.method() === 'DELETE') {
      deleted = true;
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    if (url.endsWith('/api/library/papers/locale-1/')) {
      await fulfillJson(route, paper);
      return;
    }

    await fulfillJson(route, { count: deleted ? 0 : 1, results: deleted ? [] : [paper] });
  });

  await page.goto('/library/papers');
  await expect(page.getByRole('heading', { name: 'Paper library' })).toBeVisible();
  await expect(page.getByText(/论文|选择文件|下载论文/)).toHaveCount(0);

  await page.getByLabel('PDF file').setInputFiles({
    name: 'locale.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 locale'),
  });
  await page.getByRole('button', { name: 'Import PDF' }).click();
  await expect(page.getByText('Accepted: Imported Locale Paper')).toBeVisible();

  await page.getByRole('button', { name: /Open paper Locale Review Paper/ }).click();
  await expect(page.getByText('In-page viewer')).toBeVisible();
  await page.getByRole('button', { name: 'Rename paper' }).click();
  await page.getByLabel('New paper title').fill('Renamed Locale Paper');
  await page.getByRole('button', { name: 'Save title' }).click();
  await expect(page.getByText('Renamed Locale Paper').first()).toBeVisible();

  await page.getByRole('button', { name: /Download Renamed Locale Paper/ }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Download started' })).toContainText(
    'Download started: Renamed Locale Paper.pdf',
  );

  await page.getByRole('button', { name: 'Delete paper' }).click();
  await expect(page.getByText('The paper will leave ordinary browse, open, and download workflows.')).toBeVisible();
  await page.getByLabel('Delete reason').fill('English validation');
  await page.getByRole('button', { name: 'Confirm delete' }).click();
  await expect(page.getByText('No shared papers are available yet.')).toBeVisible();
  await expect(page.getByText(/论文|选择文件|下载论文/)).toHaveCount(0);
});
