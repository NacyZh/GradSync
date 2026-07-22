import { expect, test, type Page } from '@playwright/test';

import { fulfillJson, mockUnavailableTokenRefresh } from './api-mocks';

const activeUser = {
  id: 10,
  email: 'advisor@example.edu',
  name: 'Advisor One',
  global_role: 'advisor',
  status: 'active',
};

async function mockSharedWorkspaceApi(page: Page) {
  await mockUnavailableTokenRefresh(page);
  await page.route('**/api/accounts/me/', async (route) => fulfillJson(route, activeUser));
  await page.route('**/api/accounts/logout/', async (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/projects/?**', async (route) => fulfillJson(route, { results: [] }));
  await page.route('**/api/notifications/**', async (route) => fulfillJson(route, { results: [] }));
  await page.route('**/api/library/papers/**', async (route) => {
    await fulfillJson(route, {
      count: 1,
      results: [{
        id: 'paper-1',
        projectId: '1',
        title: 'Shared Boundary Paper',
        canonicalTitle: 'Shared Boundary Paper',
        authors: ['Ada Lovelace'],
        publicationYear: 2026,
        visibility: 'group_wide',
        boundaryType: 'standalone_shared',
        sourceProject: null,
        status: 'active',
        downloadAvailable: true,
        actionCapabilities: { canView: true, canDownload: true, canRename: false, canDelete: false },
      }],
    });
  });
  await page.route('**/api/library/code/**', async (route) => {
    await fulfillJson(route, {
      count: 1,
      results: [{
        id: 'code-1',
        projectId: '1',
        name: 'Shared Boundary Code',
        description: 'Reusable archive',
        visibility: 'group_wide',
        boundaryType: 'standalone_shared',
        sourceProject: null,
        status: 'active',
        archiveFileId: 'archive-1',
        actionCapabilities: { canView: true, canDownload: true, canRename: false, canDelete: false },
      }],
    });
  });
  await page.route('**/api/library/documents/**', async (route) => {
    await fulfillJson(route, {
      count: 1,
      results: [{
        id: 'doc-1',
        projectId: '1',
        categoryId: 'cat-1',
        categoryName: 'Protocols',
        title: 'Shared Boundary Document',
        visibility: 'group_wide',
        boundaryType: 'standalone_shared',
        sourceProject: null,
        status: 'active',
        actionCapabilities: { canView: true, canDownload: true, canRename: false, canDelete: false, canUploadGroupWide: false },
      }],
    });
  });
  await page.route('**/api/document-categories**', async (route) => {
    await fulfillJson(route, [{ id: 'cat-1', name: 'Protocols', description: '', status: 'active' }]);
  });
  await page.route('**/api/code-artifacts/upload-policy/**', async (route) => {
    await fulfillJson(route, {
      category: 'code',
      maxSizeBytes: 1048576,
      displayLabel: '1 MB',
      allowedExtensions: ['.zip'],
      contentTypes: ['application/zip'],
    });
  });
}

async function expectStandaloneNavigation(page: Page) {
  await expect(page.getByRole('link', { name: 'Papers' })).toHaveAttribute('href', '/library/papers');
  await expect(page.getByRole('link', { name: 'Code' })).toHaveAttribute('href', '/library/code');
  await expect(page.getByRole('link', { name: 'Documents' })).toHaveAttribute('href', '/library/documents');
}

async function expectNoProjectMetadataLeakage(page: Page) {
  await expect(page.getByText(/private writing title|project-only material/i)).toHaveCount(0);
}

async function visitOldProjectLink(page: Page, section: 'papers' | 'code' | 'documents' | 'writing') {
  await page.goto(`/projects/1/${section}`);
}

test.describe('shared workspace boundaries helpers', () => {
  test.beforeEach(async ({ page }) => {
    await mockSharedWorkspaceApi(page);
  });

  test('standalone shared sections are reachable from primary navigation', async ({ page }) => {
    await page.goto('/');
    await expectStandaloneNavigation(page);
    await page.getByRole('link', { name: 'Code' }).click();
    await expect(page).toHaveURL(/\/library\/code$/);
    await expect(page.getByTestId('code-results-list')).toContainText('Shared Boundary Code');
    await page.getByRole('link', { name: 'Documents' }).click();
    await expect(page).toHaveURL(/\/library\/documents$/);
    await expect(page.getByTestId('document-results-list')).toContainText('Shared Boundary Document');
  });

  test('old project links do not leak hidden metadata', async ({ page }) => {
    await visitOldProjectLink(page, 'papers');
    await expect(page).toHaveURL(/\/library\/papers$/);
    await visitOldProjectLink(page, 'code');
    await expect(page).toHaveURL(/\/library\/code$/);
    await visitOldProjectLink(page, 'documents');
    await expect(page).toHaveURL(/\/library\/documents$/);
    await visitOldProjectLink(page, 'writing');
    await expect(page).toHaveURL(/\/writing$/);
    await expectNoProjectMetadataLeakage(page);
  });

  test('project materials visibility journey shows controlled project-owned area', async ({ page }) => {
    let materialVisibility: 'project-only' | 'group-wide' = 'project-only';
    await page.route('**/api/projects/1/materials/44/visibility/', async (route) => {
      materialVisibility = 'group-wide';
      await fulfillJson(route, {
        id: '44',
        materialType: 'document',
        backingRecordId: '9',
        displayName: 'Project Protocol',
        sourceProject: { id: '1', title: 'Boundary Project' },
        visibility: materialVisibility,
        classificationState: 'active',
        actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: true },
      });
    });
    await page.route(/\/api\/projects\/1\/materials\/(\?.*)?$/, async (route) => {
      await fulfillJson(route, {
        count: 1,
        results: [{
          id: '44',
          materialType: 'document',
          backingRecordId: '9',
          displayName: 'Project Protocol',
          sourceProject: { id: '1', title: 'Boundary Project' },
          visibility: materialVisibility,
          classificationState: 'active',
          actionCapabilities: { canView: true, canDownload: true, canChangeVisibility: true },
        }],
      });
    });

    await page.goto('/projects/1/materials');
    await expect(page.getByRole('heading', { name: 'Project materials', exact: true })).toBeVisible();
    const materialList = page.getByLabel('Project material list');
    await expect(materialList.getByText('Project Protocol')).toBeVisible();
    await expect(materialList.getByText('Source: Boundary Project')).toBeVisible();
    await expect(materialList.getByText('Project-only', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Set group-wide' }).click();
    await expect(materialList.getByText('Group-wide', { exact: true })).toBeVisible();
  });
});
