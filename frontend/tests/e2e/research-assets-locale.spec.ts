import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page);
});

test('paper import, code download, and locale persistence workflow is reachable', async ({ page }) => {
  if (!fullStackE2E) {
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

  await page.goto('/projects/1/papers');
  await expect(page.getByRole('heading', { name: 'Paper library' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Graph Neural Methods' })).toBeVisible();
  await page.getByLabel('Paper title').fill('Graph Neural Methods');
  await page.getByLabel('First author').fill('Lin Chen');
  await page.getByRole('button', { name: 'Import' }).click();
  await expect(page.getByRole('alert')).toContainText('Duplicate paper detected');
  await page.getByRole('button', { name: 'Download' }).click();
  await expect(page.getByRole('status')).toContainText('graph.pdf');

  await page.goto('/projects/1/code');
  await expect(page.getByRole('heading', { name: 'Code repository' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Simulator' })).toBeVisible();
  await page.getByRole('button', { name: 'Download' }).click();
  await expect(page.getByRole('status')).toContainText('sim.zip');

  await page.getByRole('button', { name: /Language|语言/ }).click();
});
