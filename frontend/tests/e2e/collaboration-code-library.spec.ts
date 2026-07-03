import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test('code archive upload, search, and download flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;

  await page.route('**/api/code-artifacts/*/download', async (route) => {
    await fulfillJson(route, { filename: 'uploaded.zip', deliveryMode: 'direct_response' });
  });

  await page.route('**/api/projects/1/code-artifacts/**', async (route) => {
    const request = route.request();
    if (request.url().includes('/download')) {
      await fulfillJson(route, { filename: 'uploaded.zip', deliveryMode: 'direct_response' });
      return;
    }
    if (request.method() === 'POST') {
      uploaded = true;
      await fulfillJson(route, {
        id: '5',
        projectId: '1',
        name: 'Uploaded Archive',
        description: 'Searchable implementation archive',
        tags: ['python'],
        visibility: 'project_members',
        checksumSha256: 'e'.repeat(64),
        archiveFileId: '12',
        status: 'active',
      }, 201);
      return;
    }
    await fulfillJson(route, {
      results: uploaded
        ? [{
            id: '5',
            projectId: '1',
            name: 'Uploaded Archive',
            description: 'Searchable implementation archive',
            tags: ['python'],
            visibility: 'project_members',
            checksumSha256: 'e'.repeat(64),
            archiveFileId: '12',
            status: 'active',
          }]
        : [{
            id: '3',
            projectId: '1',
            name: 'Group Code Archive',
            description: 'Microscopy analysis archive',
            tags: ['analysis'],
            visibility: 'group_wide',
            checksumSha256: 'c'.repeat(64),
            archiveFileId: '9',
            status: 'active',
          }],
    });
  });

  await page.goto('/projects/1/code');
  await expect(page.getByRole('heading', { name: 'Group Code Archive' })).toBeVisible();
  await expect(page.getByLabel('Code artifact detail').getByText('group wide', { exact: true })).toBeVisible();

  await page.getByPlaceholder('Search name, description, tag').fill('Archive');
  await page.getByLabel('Archive file').setInputFiles({
    name: 'uploaded.zip',
    mimeType: 'application/zip',
    buffer: Buffer.from('zip'),
  });
  await page.getByLabel('Artifact name').fill('Uploaded Archive');
  await page.getByLabel('Artifact description').fill('Searchable implementation archive');
  await page.getByRole('button', { name: 'Upload archive' }).click();
  await expect(page.getByText('Upload complete')).toBeVisible();

  await page.getByRole('button', { name: /Download/ }).click();
  await expect(page.getByText(/uploaded.zip/)).toBeVisible();
});
