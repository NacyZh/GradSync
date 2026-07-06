import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('shared paper library search and download does not require project membership', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let imported = false;

  if (!fullStackE2E) {
    await page.route('**/api/library/papers/**', async (route) => {
      const request = route.request();
      const url = request.url();
      if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
        imported = true;
        await fulfillJson(
          route,
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
          202,
        );
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
  }
});
