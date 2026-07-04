import { expect, test, type Page } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

async function mockCollaborationPages(page: Page) {
  await mockAuthenticatedApi(page);
  await page.route('**/api/document-categories**', async (route) => fulfillJson(route, [{ id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' }]));
  await page.route('**/api/projects/1/papers/**', async (route) => fulfillJson(route, { results: [{ id: '1', projectId: '1', title: 'Group Wide Graph Paper', authors: ['Lin Chen'], publicationYear: 2025, visibility: 'group_wide', status: 'active', attachments: [{ id: '11', filename: 'graph.pdf', checksumSha256: 'a'.repeat(64), status: 'active' }] }] }));
  await page.route('**/api/projects/1/code-artifacts/**', async (route) => fulfillJson(route, { results: [{ id: '3', projectId: '1', name: 'Group Code Archive', description: 'Microscopy analysis archive', tags: ['analysis'], visibility: 'group_wide', checksumSha256: 'c'.repeat(64), archiveFileId: '9', status: 'active' }] }));
  await page.route('**/api/projects/1/documents**', async (route) => fulfillJson(route, { results: [{ id: '4', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: 'Microscope Protocol', description: 'Calibration workflow', visibility: 'group_wide', uploaderId: '10', checksumSha256: 'a'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }] }));
  await page.route('**/api/projects/1/writing-projects/**', async (route) => fulfillJson(route, { results: [{ id: '2', projectId: '1', studentId: '5', title: 'Thesis Chapter', writingType: 'thesis', status: 'active', versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, draftFileName: 'chapter.docx', fileKind: 'word', status: 'feedback_available', feedback: [] }] }] }));
  await page.route('**/api/resources/', async (route) => fulfillJson(route, { results: [{ id: 7, name: 'Confocal microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.', useSubmissions: [] }] }));
  await page.route('**/api/resource-items/', async (route) => fulfillJson(route, { results: [{ id: 41, resourceTypeId: 1, name: 'Confocal microscope', status: 'available', available: true }] }));
  await page.route('**/api/resource-types/', async (route) => fulfillJson(route, { results: [{ id: 1, name: 'Microscope', scope: 'global', fieldSchema: [], status: 'active' }] }));
  await page.route('**/api/projects/1/bookings/', async (route) => fulfillJson(route, { results: [] }));
}

async function expectNoLayoutOverflow(page: Page) {
  const issues = await page.evaluate(() => {
    const overflow: string[] = [];
    if (document.documentElement.scrollWidth > window.innerWidth + 1) {
      overflow.push(`document overflow ${document.documentElement.scrollWidth}/${window.innerWidth}`);
    }
    for (const element of Array.from(document.querySelectorAll('button, a, input, select, textarea, [role="button"]'))) {
      const html = element as HTMLElement;
      const rect = html.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0 || rect.bottom < 0 || rect.top > window.innerHeight) continue;
      if (html.scrollWidth > html.clientWidth + 2) {
        overflow.push(`${html.tagName.toLowerCase()} text overflow: ${html.textContent?.trim() || html.getAttribute('aria-label') || html.getAttribute('name') || 'control'}`);
      }
    }
    return overflow;
  });
  expect(issues).toEqual([]);
}

for (const viewport of [
  { width: 390, height: 844, label: 'mobile' },
  { width: 1280, height: 900, label: 'desktop' },
]) {
  test(`collaboration pages keep landmarks and controls accessible on ${viewport.label}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockCollaborationPages(page);
    for (const path of ['/projects/1', '/projects/1/papers', '/projects/1/code', '/projects/1/documents', '/projects/1/writing', '/projects/1/resources']) {
      await page.goto(path);
      await expect(page.getByRole('banner')).toBeVisible();
      await expect(page.getByRole('main')).toBeVisible();
      await expect(page.getByRole('navigation', { name: 'Primary workspace' })).toBeVisible();
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus-visible').first()).toBeVisible();
      await expectNoLayoutOverflow(page);
    }
  });
}
