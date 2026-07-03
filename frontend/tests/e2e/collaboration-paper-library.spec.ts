import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test('paper library visibility, upload, search, and download flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;

  await page.route('**/api/projects/1/papers/**', async (route) => {
    const request = route.request();
    if (request.method() === 'POST' && request.url().endsWith('/download/')) {
      await fulfillJson(route, { filename: 'graph.pdf', deliveryMode: 'direct_response' });
      return;
    }
    if (request.method() === 'POST') {
      uploaded = true;
      await fulfillJson(route, {
        id: '2',
        projectId: '1',
        title: 'Uploaded Graph Paper',
        authors: ['Ada Lovelace'],
        publicationYear: 2026,
        visibility: 'project_members',
        status: 'active',
        attachments: [{ id: '12', filename: 'uploaded.pdf', checksumSha256: 'b'.repeat(64), status: 'active' }],
      }, 201);
      return;
    }
    await fulfillJson(route, {
      results: uploaded
        ? [{
            id: '2',
            projectId: '1',
            title: 'Uploaded Graph Paper',
            authors: ['Ada Lovelace'],
            publicationYear: 2026,
            visibility: 'project_members',
            status: 'active',
            attachments: [{ id: '12', filename: 'uploaded.pdf', checksumSha256: 'b'.repeat(64), status: 'active' }],
          }]
        : [{
            id: '1',
            projectId: '1',
            title: 'Group Wide Graph Paper',
            authors: ['Lin Chen'],
            publicationYear: 2025,
            visibility: 'group_wide',
            status: 'active',
            attachments: [{ id: '11', filename: 'graph.pdf', checksumSha256: 'a'.repeat(64), status: 'active' }],
          }],
    });
  });

  await page.goto('/projects/1/papers');
  await expect(page.getByRole('heading', { name: 'Group Wide Graph Paper' })).toBeVisible();
  await expect(page.getByLabel('Paper detail').getByText('group wide', { exact: true })).toBeVisible();

  await page.getByPlaceholder('Search title, author, year, keyword').fill('Graph');
  await page.getByLabel('PDF file').setInputFiles({
    name: 'uploaded.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4'),
  });
  await page.getByLabel('Paper title').fill('Uploaded Graph Paper');
  await page.getByLabel('Authors').fill('Ada Lovelace');
  await page.getByRole('button', { name: 'Upload paper' }).click();
  await expect(page.getByText('Upload complete')).toBeVisible();

  await page.getByRole('button', { name: /Download/ }).click();
  await expect(page.getByText(/uploaded.pdf|graph.pdf/)).toBeVisible();
});
