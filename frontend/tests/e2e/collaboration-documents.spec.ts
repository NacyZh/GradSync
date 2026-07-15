import { expect, test, type Page } from '@playwright/test';

import {
  buildDocumentCategory,
  buildDocumentRecord,
  buildLongDocumentRecord,
  fulfillJson,
  fullStackE2E,
  loginAs,
  mockAuthenticatedApi,
} from './api-mocks';

async function mockDocumentLibrary(page: Page) {
  await mockAuthenticatedApi(page);
  if (fullStackE2E) {
    return;
  }
  let uploaded = false;
  let lastUploadBody = '';
  const categories = [
    buildDocumentCategory({ id: '1', name: 'Protocols', description: 'Lab protocols' }),
    buildDocumentCategory({ id: '2', name: 'Reports', description: 'Research reports' }),
  ];
  await page.route('**/api/document-categories**', async (route) => fulfillJson(route, categories));
  await page.route('**/api/library/documents/*/download/', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="protocol.pdf"',
      },
      body: Buffer.from('document'),
    });
  });
  await page.route('**/api/projects/1/materials/44/download/', async (route) => {
    await fulfillJson(route, {
      filename: 'Project Protocol.pdf',
      deliveryMode: 'direct_response',
      url: '',
      expiresAt: '2026-07-15T00:00:00Z',
    });
  });
  await page.route('**/api/projects/1/materials/45/download/', async (route) => {
    await fulfillJson(route, { message: 'Project material is no longer available' }, 410);
  });
  await page.route('**/api/projects/1/materials/', async (route) => {
    await fulfillJson(route, {
      count: 1,
      results: [
        {
          id: '44',
          materialType: 'document',
          backingRecordId: '4',
          displayName: 'Project Protocol',
          sourceProject: { id: '1', title: 'Graphene Lab' },
          visibility: 'project-only',
          classificationState: 'active',
          actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: false },
        },
        {
          id: '45',
          materialType: 'document',
          backingRecordId: '5',
          displayName: 'Stale Project Protocol',
          sourceProject: { id: '1', title: 'Graphene Lab' },
          visibility: 'project-only',
          classificationState: 'active',
          actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: false },
        },
      ],
    });
  });
  await page.route('**/api/library/documents/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.includes('/download/')) {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="protocol.pdf"',
        },
        body: Buffer.from('document'),
      });
      return;
    }
    if (request.method() === 'POST') {
      uploaded = true;
      lastUploadBody = request.postData() ?? '';
      await fulfillJson(
        route,
        buildDocumentRecord({
          id: '5',
          title: 'Uploaded Protocol',
          visibility: 'group_wide',
        }),
        201,
      );
      return;
    }
    const selectedCategory = url.searchParams.get('categoryId');
    await fulfillJson(route, {
      results: uploaded
        ? [buildDocumentRecord({ id: '5', title: 'Uploaded Protocol', visibility: 'group_wide' })]
        : selectedCategory === '2'
          ? []
          : [buildDocumentRecord(), buildLongDocumentRecord()],
    });
  });
  return {
    lastUploadBody: () => lastUploadBody,
  };
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.innerWidth + 1);
  expect(overflow.bodyScrollWidth).toBeLessThanOrEqual(overflow.innerWidth + 1);
}

test('document library upload, shared category, search, list, detail, and download regions are reachable', async ({ page }) => {
  const documentMocks = await mockDocumentLibrary(page);

  if (fullStackE2E) {
    await loginAs(page);
  }
  await page.goto('/library/documents');

  await expect(page.getByRole('heading', { name: 'Shared documents' })).toBeVisible();
  await expect(page.getByText('Example Protocol')).toBeHidden();
  await expect(page.getByLabel('Document library upload and download region')).toBeVisible();
  await expect(page.getByLabel('Document library search and display region')).toBeVisible();
  await expect(page.getByText('Categorized document upload')).toBeVisible();

  if (fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('No document selected');
    await expect(page.getByRole('button', { name: /^Category / }).first()).toBeVisible();
    await expect(page.getByTestId('document-selected-detail-region')).toContainText('No document selected');
  } else {
    await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('Microscope Protocol');
    await expect(page.getByRole('button', { name: 'Category Protocols' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Select document Microscope Protocol/ })).toBeVisible();
    await expect(page.getByTestId('document-selected-detail-region')).toContainText('Microscope Protocol');

    await page.getByPlaceholder('Search title, category, description').fill('Protocol');
    await page.getByRole('button', { name: 'Category Reports' }).click();
    await expect(page.getByText('No document search results')).toBeVisible();
    await page.getByRole('button', { name: 'Category Protocols' }).click();
    await expect(page.getByRole('button', { name: /Select document Microscope Protocol/ })).toBeVisible();
  }

  await page.getByLabel('Document file').setInputFiles({
    name: fullStackE2E ? 'uploaded-document.txt' : 'uploaded.md',
    mimeType: fullStackE2E ? 'text/plain' : 'text/markdown',
    buffer: Buffer.from('# protocol'),
  });
  await expect(page.getByText(`Selected document: ${fullStackE2E ? 'uploaded-document.txt' : 'uploaded.md'}`)).toBeVisible();
  await page.getByRole('button', { name: 'Clear selected file' }).click();
  await expect(page.getByText(`Selected document: ${fullStackE2E ? 'uploaded-document.txt' : 'uploaded.md'}`)).toBeHidden();
  await page.getByLabel('Document file').setInputFiles({
    name: fullStackE2E ? 'uploaded-document.txt' : 'uploaded.md',
    mimeType: fullStackE2E ? 'text/plain' : 'text/markdown',
    buffer: Buffer.from('# protocol'),
  });
  await page.getByRole('button', { name: 'Upload document' }).click();
  await expect(page.getByText('Upload complete')).toBeVisible();
  if (fullStackE2E) {
    await expect(page.getByRole('button', { name: /Select document uploaded-document/ })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('uploaded-document');
  } else {
    expect(documentMocks?.lastUploadBody()).toContain('name="file"');
    expect(documentMocks?.lastUploadBody()).toContain('name="categoryId"');
    expect(documentMocks?.lastUploadBody()).not.toContain('name="title"');
  }

  if (fullStackE2E) {
    await page.getByRole('button', { name: /Download/ }).click();
    await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('uploaded-document');
  } else {
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /Download/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('protocol.pdf');
    await expect(page.getByText(/protocol.pdf/)).toBeVisible();
  }
});

test('project material document download stays inside project materials workspace', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked project material download coverage uses deterministic fixtures.');
  await mockDocumentLibrary(page);

  await page.goto('/projects/1/materials');
  await expect(page.getByRole('heading', { name: 'Project materials' })).toBeVisible();
  await expect(page.getByText('Project Protocol', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Download Project Protocol' }).click();
  await expect(page.getByText('Download ready: Project Protocol.pdf', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Download Stale Project Protocol' }).click();
  await expect(page.getByText('Project material is no longer available', { exact: true })).toBeVisible();
});

test('standalone shared documents hide project-level rename and delete actions', async ({ page }) => {
  test.skip(fullStackE2E, 'Mock-mode standalone boundary coverage; API tests cover mutations.');

  await mockAuthenticatedApi(page);
  const documents = [
    buildDocumentRecord({
      id: '4',
      title: 'Microscope Protocol',
      actionCapabilities: {
        canView: true,
        canDownload: true,
        canRename: true,
        canDelete: true,
        canUploadGroupWide: true,
      },
    }),
    buildDocumentRecord({
      id: '5',
      title: 'Delete Candidate',
      actionCapabilities: {
        canView: true,
        canDownload: true,
        canRename: true,
        canDelete: true,
        canUploadGroupWide: true,
      },
    }),
  ];
  await page.route('**/api/document-categories**', async (route) =>
    fulfillJson(route, [buildDocumentCategory({ id: '1', name: 'Protocols' })]),
  );
  await page.route('**/api/library/documents/**', async (route) => fulfillJson(route, { results: documents }));

  await page.goto('/library/documents');
  await expect(page.getByTestId('document-selected-detail-region')).toContainText('Microscope Protocol');
  await expect(page.getByRole('button', { name: 'Rename document' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete document' })).toHaveCount(0);
});

test('document selected download shows errors and no-selection state clearly', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked selected-download coverage uses deterministic fixtures.');

  await page.setViewportSize({ width: 390, height: 844 });
  await mockAuthenticatedApi(page);
  let hasDocument = true;
  await page.route('**/api/document-categories**', async (route) =>
    fulfillJson(route, [buildDocumentCategory({ id: '1', name: 'Protocols' })]),
  );
  await page.route('**/api/library/documents/**', async (route) =>
    route.request().url().includes('/download/')
      ? fulfillJson(route, { message: 'Document is no longer available' }, 410)
      : fulfillJson(route, { results: hasDocument ? [buildDocumentRecord()] : [] }),
  );
  await page.route('**/api/library/documents/*/download/', async (route) =>
    fulfillJson(route, { message: 'Document is no longer available' }, 410),
  );

  await page.goto('/library/documents');
  await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('Microscope Protocol');
  await page.getByRole('button', { name: /Download Microscope Protocol/ }).click();
  await expect(page.getByRole('alert')).toContainText('Document is no longer available');

  hasDocument = false;
  await page.getByPlaceholder('Search title, category, description').fill('empty');
  await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('No document selected');
  await expect(page.getByRole('button', { name: 'Download', exact: true })).toBeDisabled();
  await expectNoHorizontalOverflow(page);
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 768, height: 900 },
  { width: 390, height: 844 },
]) {
  test(`document library papers-style layout has no horizontal overflow at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockDocumentLibrary(page);
    if (fullStackE2E) {
      await loginAs(page);
    }
    await page.goto('/library/documents');

    await expect(page.getByLabel('Document library upload and download region')).toBeVisible();
    await expect(page.getByLabel('Document library search and display region')).toBeVisible();
    await expect(page.getByTestId('document-selected-detail-region')).toBeVisible();
    if (!fullStackE2E) {
      await expect(page.getByTestId('document-results-list')).toBeVisible();
    }
    await expectNoHorizontalOverflow(page);
  });
}
