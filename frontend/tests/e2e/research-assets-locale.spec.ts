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
        await fulfillJson(route, { filename: 'Graph Neural Methods.pdf', deliveryMode: 'direct_response' });
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
  await expect(page.getByText('Duplicate: Graph Neural Methods')).toBeVisible();
  await page.getByRole('button', { name: /Download Graph Neural Methods/ }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Download ready' })).toContainText('Graph Neural Methods.pdf');

  await page.goto('/projects/1/code');
  await expect(page.getByRole('heading', { name: 'Code repository' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Simulator' })).toBeVisible();
  await page.getByRole('button', { name: 'Download' }).click();
  await expect(page.getByRole('status')).toContainText('sim.zip');

  await page.getByRole('button', { name: /Language|语言/ }).click();
});
