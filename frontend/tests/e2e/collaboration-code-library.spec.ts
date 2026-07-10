import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

function codeArtifactFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: '3',
    projectId: '1',
    name: 'Group Code Archive',
    description: 'Microscopy analysis archive',
    tags: ['analysis'],
    visibility: 'group_wide',
    checksumSha256: 'c'.repeat(64),
    archiveFileId: '9',
    status: 'active',
    actionCapabilities: {
      canView: true,
      canDownload: true,
      canRename: false,
      canDelete: false,
    },
    latestVersion: {
      id: 'version-3',
      artifactId: '3',
      projectId: '1',
      versionLabel: 'v1',
      filename: 'group-code.zip',
      checksumSha256: 'c'.repeat(64),
      status: 'active',
    },
    ...overrides,
  };
}

async function expectCodeLayoutStable(page: Page) {
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
    const list = document.querySelector('[data-testid="code-results-list"]');
    const parentRect = list?.getBoundingClientRect();
    if (!parentRect) {
      overflow.push('missing code-results-list');
    } else {
      for (const [index, element] of Array.from(document.querySelectorAll('[data-testid="code-result-row"]')).entries()) {
        const html = element as HTMLElement;
        const rect = html.getBoundingClientRect();
        if (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1) {
          overflow.push(`row ${index} outside parent`);
        }
        if (html.scrollWidth > html.clientWidth + 2) {
          overflow.push(`row ${index} internal overflow`);
        }
      }
    }
    return overflow;
  });
  expect(issues).toEqual([]);
}

test('code archive upload, search, and download flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;

  if (!fullStackE2E) {
    await page.route('**/api/library/code/**', async (route) => {
      const request = route.request();
      if (request.url().includes('/download')) {
        await fulfillJson(route, { filename: 'uploaded.zip', deliveryMode: 'direct_response' });
        return;
      }
      if (request.method() === 'POST') {
        uploaded = true;
        await fulfillJson(
          route,
          {
            ...codeArtifactFixture({
              id: '5',
              name: 'Uploaded Archive',
              description: 'Searchable implementation archive',
              tags: ['python'],
              visibility: 'project_members',
              checksumSha256: 'e'.repeat(64),
              archiveFileId: '12',
            }),
          },
          201,
        );
        return;
      }
      await fulfillJson(route, {
        results: uploaded
          ? [
              codeArtifactFixture({
                id: '5',
                name: 'Uploaded Archive',
                description: 'Searchable implementation archive',
                tags: ['python'],
                visibility: 'project_members',
                checksumSha256: 'e'.repeat(64),
                archiveFileId: '12',
              }),
            ]
          : [
              codeArtifactFixture(),
            ],
      });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
    await page.goto('/library/code');
    await expect(page.getByRole('heading', { name: 'Shared code' })).toBeVisible();
    await expect(page.getByTestId('code-selected-detail-region').getByRole('heading', { name: 'Analysis Toolkit' })).toBeVisible();
    await page.getByRole('button', { name: 'Download', exact: true }).click();
    await expect(page.getByRole('status')).toContainText('analysis-toolkit.zip');
    return;
  }

  await page.goto('/library/code');
  await expect(page.getByTestId('code-selected-detail-region').getByRole('heading', { name: 'Group Code Archive' })).toBeVisible();
  await expect(page.getByTestId('code-selected-detail-region').getByText('group wide', { exact: true })).toBeVisible();

  await page.getByPlaceholder('Search name, description, tag').fill('Archive');
  await expect(page.getByRole('button', { name: 'Choose archive' })).toBeVisible();
  await expect(page.getByText(/Allowed archives: .7z, .bz2, .gz, .tar, .tgz, .xz, .zip up to 100 MB/)).toBeVisible();
  await page.getByLabel('Archive file').setInputFiles({
    name: 'draft.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('bad'),
  });
  await expect(page.getByRole('alert')).toContainText('Choose a supported archive file');
  await page.getByRole('button', { name: 'Clear selected archive' }).click();
  await expect(page.getByText('draft.txt')).toHaveCount(0);
  await page.getByLabel('Archive file').setInputFiles({
    name: 'uploaded.zip',
    mimeType: 'application/zip',
    buffer: Buffer.from('zip'),
  });
  await expect(page.getByText('Selected archive: uploaded.zip')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reselect archive' })).toBeVisible();
  await page.getByLabel('Artifact name').fill('Uploaded Archive');
  await page.getByLabel('Artifact description').fill('Searchable implementation archive');
  await page.getByRole('button', { name: 'Upload archive' }).click();
  await expect(page.getByText('Upload complete')).toBeVisible();
  await expect(page.getByTestId('code-selected-detail-region')).toContainText('Uploaded Archive');

  await page.getByRole('button', { name: 'Download', exact: true }).click();
  await expect(page.getByText(/uploaded.zip/)).toBeVisible();
});

test('code repository layout remains stable across desktop and narrow widths', async ({ page }) => {
  await mockAuthenticatedApi(page);

  if (!fullStackE2E) {
    await page.route('**/api/library/code/**', async (route) => {
      if (route.request().url().includes('/download')) {
        await fulfillJson(route, { filename: 'long-code.zip', deliveryMode: 'direct_response' });
        return;
      }
      await fulfillJson(route, {
        results: [
          codeArtifactFixture({
            id: 'long',
            name: 'Simulation pipeline with exceptionally long repository archive name for responsive layout validation',
            description: 'Long description '.repeat(24),
            tags: ['simulation', 'very-long-tag-name-for-layout', 'reproducibility'],
            sourcePathLabel: 'archives/' + 'nested-path-'.repeat(12) + 'source.zip',
            latestVersion: {
              id: 'version-long',
              artifactId: 'long',
              projectId: '1',
              versionLabel: 'release-candidate-with-long-label',
              filename: 'very-long-source-archive-name-for-layout-validation.zip',
              checksumSha256: 'f'.repeat(64),
              status: 'active',
            },
          }),
          codeArtifactFixture({ id: 'short', name: 'Short Utility', archiveFileId: '12' }),
        ],
      });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
  }

  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/library/code');
    await expect(page.getByTestId('code-repository-workspace')).toBeVisible();
    await expect(page.getByLabel('Code repository upload and download region')).toBeVisible();
    await expect(page.getByLabel('Code repository search and display region')).toBeVisible();
    await expectCodeLayoutStable(page);
  }
});

test('standalone shared code hides project-level rename and delete actions', async ({ page }) => {
  test.skip(fullStackE2E, 'Mock-mode standalone boundary coverage; API tests cover mutations.');
  await mockAuthenticatedApi(page);
  const artifacts = [
    codeArtifactFixture({
      id: 'rename-target',
      name: 'Analysis Pipeline',
      actionCapabilities: {
        canView: true,
        canDownload: true,
        canRename: true,
        canDelete: true,
      },
    }),
    codeArtifactFixture({
      id: 'delete-target',
      name: 'Delete Candidate',
      archiveFileId: '10',
      actionCapabilities: {
        canView: true,
        canDownload: true,
        canRename: true,
        canDelete: true,
      },
      latestVersion: {
        id: 'version-delete',
        artifactId: 'delete-target',
        projectId: '1',
        versionLabel: 'v1',
        filename: 'delete.zip',
        checksumSha256: 'd'.repeat(64),
        status: 'active',
      },
    }),
  ];

  await page.route('**/api/library/code/**', async (route) => {
    await fulfillJson(route, { results: artifacts });
  });

  await page.goto('/library/code');
  await expect(page.getByTestId('code-selected-detail-region')).toContainText('Analysis Pipeline');
  await expect(page.getByRole('button', { name: 'Rename code artifact' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete code artifact' })).toHaveCount(0);
});

test('non-maintainer cannot see rename or delete actions', async ({ page }) => {
  test.skip(fullStackE2E, 'Mock-mode permission visibility coverage; full-stack permissions are covered by API tests.');
  await mockAuthenticatedApi(page);
  await page.route('**/api/library/code/**', async (route) => {
    await fulfillJson(route, { results: [codeArtifactFixture({ name: 'Read Only Archive' })] });
  });

  await page.goto('/library/code');

  await expect(page.getByTestId('code-selected-detail-region')).toContainText('Read Only Archive');
  await expect(page.getByRole('button', { name: 'Rename code artifact' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete code artifact' })).toHaveCount(0);
});
