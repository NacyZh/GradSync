import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test('document library category retrieval, upload, search, and download flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;

  await page.route('**/api/document-categories**', async (route) => {
    await fulfillJson(route, [
      { id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' },
      { id: '2', name: 'Reports', description: 'Research reports', status: 'active' },
      { id: '3', name: 'Meetings', description: 'Meeting notes', status: 'active' },
    ]);
  });

  await page.route('**/api/documents/*/download', async (route) => {
    await fulfillJson(route, { filename: 'protocol.pdf', deliveryMode: 'direct_response' });
  });

  await page.route('**/api/projects/1/documents**', async (route) => {
    const request = route.request();
    if (request.method() === 'POST') {
      uploaded = true;
      await fulfillJson(route, {
        id: '5',
        projectId: '1',
        categoryId: '1',
        categoryName: 'Protocols',
        title: 'Uploaded Protocol',
        description: 'Shared instructions',
        visibility: 'project_members',
        uploaderId: '10',
        checksumSha256: 'b'.repeat(64),
        createdAt: '2026-07-03T08:00:00Z',
        status: 'active',
      }, 201);
      return;
    }
    await fulfillJson(route, {
      results: uploaded
        ? [{
            id: '5',
            projectId: '1',
            categoryId: '1',
            categoryName: 'Protocols',
            title: 'Uploaded Protocol',
            description: 'Shared instructions',
            visibility: 'project_members',
            uploaderId: '10',
            checksumSha256: 'b'.repeat(64),
            createdAt: '2026-07-03T08:00:00Z',
            status: 'active',
          }]
        : [{
            id: '4',
            projectId: '1',
            categoryId: '1',
            categoryName: 'Protocols',
            title: 'Microscope Protocol',
            description: 'Calibration workflow',
            visibility: 'group_wide',
            uploaderId: '10',
            checksumSha256: 'a'.repeat(64),
            createdAt: '2026-07-03T08:00:00Z',
            status: 'active',
          }],
    });
  });

  await page.goto('/projects/1/documents');
  await expect(
    page.getByLabel('Category browser').getByRole('button', { name: /Protocols/ }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Microscope Protocol' })).toBeVisible();
  await expect(page.getByLabel('Document detail').getByText('group wide', { exact: true })).toBeVisible();

  await page.getByPlaceholder('Search title, category, description').fill('Protocol');
  await page.getByLabel('Document file').setInputFiles({
    name: 'uploaded.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from('# protocol'),
  });
  await page.getByLabel('Document title').fill('Uploaded Protocol');
  await page.getByLabel('Document category').selectOption('1');
  await page.getByLabel('Document description').fill('Shared instructions');
  await page.getByRole('button', { name: 'Upload document' }).click();
  await expect(page.getByText('Upload complete')).toBeVisible();

  await page.getByRole('button', { name: /Download/ }).click();
  await expect(page.getByText(/protocol.pdf/)).toBeVisible();
});
