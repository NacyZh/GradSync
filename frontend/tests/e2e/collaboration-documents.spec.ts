import { expect, test, type Page } from '@playwright/test';

import {
  buildDocumentCategory,
  buildDocumentRecord,
  buildLongDocumentRecord,
  fulfillJson,
  fullStackE2E,
  loginAs,
  mockAuthenticatedApi,
  nonMaintainerDocumentCapabilities,
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
  await page.route('**/api/documents/*/download', async (route) => {
    await fulfillJson(route, { filename: 'protocol.pdf', deliveryMode: 'direct_response' });
  });
  await page.route('**/api/projects/1/documents**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === 'POST') {
      uploaded = true;
      lastUploadBody = request.postData() ?? '';
      await fulfillJson(
        route,
        buildDocumentRecord({
          id: '5',
          title: 'Uploaded Protocol',
          visibility: 'project_members',
        }),
        201,
      );
      return;
    }
    const selectedCategory = url.searchParams.get('categoryId');
    await fulfillJson(route, {
      results: uploaded
        ? [buildDocumentRecord({ id: '5', title: 'Uploaded Protocol', visibility: 'project_members' })]
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
  await page.goto('/projects/1/documents');

  await expect(page.getByRole('heading', { name: 'Document library' })).toBeVisible();
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
    await expect(page.getByText('No documents in category')).toBeVisible();
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

  await page.getByRole('button', { name: /Download/ }).click();
  if (fullStackE2E) {
    await expect(page.getByRole('region', { name: 'Selected document download' })).toContainText('uploaded-document');
  } else {
    await expect(page.getByText(/protocol.pdf/)).toBeVisible();
  }
});

test('document library maintainer can rename and delete while non-maintainer actions stay hidden', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked maintainer/non-maintainer action coverage uses deterministic fixtures.');

  await mockAuthenticatedApi(page);
  let maintainerDocuments = [
    buildDocumentRecord({ id: '4', title: 'Microscope Protocol' }),
    buildDocumentRecord({ id: '5', title: 'Delete Candidate' }),
  ];
  const requests: Array<{ method: string; url: string; body: string | null }> = [];
  await page.route('**/api/document-categories**', async (route) =>
    fulfillJson(route, [buildDocumentCategory({ id: '1', name: 'Protocols' })]),
  );
  await page.route('**/api/projects/1/documents**', async (route) => {
    const request = route.request();
    requests.push({ method: request.method(), url: request.url(), body: request.postData() });
    if (request.method() === 'PATCH') {
      maintainerDocuments = [
        buildDocumentRecord({ id: '4', title: 'Renamed Protocol' }),
        maintainerDocuments[1],
      ];
      await fulfillJson(route, maintainerDocuments[0]);
      return;
    }
    if (request.method() === 'DELETE') {
      maintainerDocuments = maintainerDocuments.filter((document) => document.id !== '5');
      await route.fulfill({ status: 204 });
      return;
    }
    await fulfillJson(route, { results: maintainerDocuments });
  });

  await page.goto('/projects/1/documents');
  await expect(page.getByTestId('document-selected-detail-region')).toContainText('Microscope Protocol');
  await page.getByRole('button', { name: 'Rename document' }).click();
  await page.getByLabel('New document title').fill('Renamed Protocol');
  await page.getByRole('button', { name: 'Save title' }).click();
  await expect(page.getByTestId('document-selected-detail-region')).toContainText('Renamed Protocol');
  expect(requests.some((request) => request.method === 'PATCH' && request.body?.includes('Renamed Protocol'))).toBe(true);

  await page.getByRole('button', { name: /Select document Delete Candidate/ }).click();
  await page.getByRole('button', { name: 'Delete document' }).click();
  await expect(page.getByText(/Delete Delete Candidate/)).toBeVisible();
  await page.getByRole('button', { name: 'Confirm delete' }).click();
  await expect(page.getByRole('button', { name: /Select document Delete Candidate/ })).toBeHidden();
  expect(requests.some((request) => request.method === 'DELETE')).toBe(true);

  await page.unroute('**/api/projects/1/documents**');
  await page.route('**/api/projects/1/documents**', async (route) =>
    fulfillJson(route, {
      results: [
        buildDocumentRecord({
          id: '6',
          title: 'Read Only Protocol',
          actionCapabilities: nonMaintainerDocumentCapabilities,
        }),
      ],
    }),
  );
  await page.goto('/projects/1/documents');
  await expect(page.getByTestId('document-selected-detail-region')).toContainText('Read Only Protocol');
  await expect(page.getByRole('button', { name: 'Rename document' })).toBeHidden();
  await expect(page.getByRole('button', { name: 'Delete document' })).toBeHidden();
});

test('document selected download shows errors and no-selection state clearly', async ({ page }) => {
  test.skip(fullStackE2E, 'Mocked selected-download coverage uses deterministic fixtures.');

  await page.setViewportSize({ width: 390, height: 844 });
  await mockAuthenticatedApi(page);
  let hasDocument = true;
  await page.route('**/api/document-categories**', async (route) =>
    fulfillJson(route, [buildDocumentCategory({ id: '1', name: 'Protocols' })]),
  );
  await page.route('**/api/projects/1/documents**', async (route) =>
    fulfillJson(route, { results: hasDocument ? [buildDocumentRecord()] : [] }),
  );
  await page.route('**/api/documents/*/download', async (route) =>
    fulfillJson(route, { message: 'Document is no longer available' }, 410),
  );

  await page.goto('/projects/1/documents');
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
    await page.goto('/projects/1/documents');

    await expect(page.getByLabel('Document library upload and download region')).toBeVisible();
    await expect(page.getByLabel('Document library search and display region')).toBeVisible();
    await expect(page.getByTestId('document-selected-detail-region')).toBeVisible();
    if (!fullStackE2E) {
      await expect(page.getByTestId('document-results-list')).toBeVisible();
    }
    await expectNoHorizontalOverflow(page);
  });
}
