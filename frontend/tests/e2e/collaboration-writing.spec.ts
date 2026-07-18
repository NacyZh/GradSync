import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, loginAs, mockAuthenticatedApi } from './api-mocks';

test('writing project feedback flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;
  let feedbackSubmitted = false;

  if (!fullStackE2E) {
    await page.route('**/api/teacher-feedback/7/download', async (route) => {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'Content-Disposition': 'attachment; filename="annotated.docx"',
        },
        body: Buffer.from('annotated feedback'),
      });
    });

    await page.route(/\/api\/writing-projects\/2\/versions\/?$/, async (route) => {
      uploaded = true;
      await fulfillJson(
        route,
        {
          id: '8',
          writingProjectId: '2',
          versionNumber: 2,
          draftFileName: 'revision.tex',
          fileKind: 'latex_source',
          status: 'submitted',
          feedback: [],
        },
        201,
      );
    });

    await page.route(/\/api\/writing-versions\/6\/feedback\/?$/, async (route) => {
      feedbackSubmitted = true;
      await fulfillJson(
        route,
        {
          id: '9',
          writingVersionId: '6',
          reviewerId: '3',
          comments: 'More notes',
          status: 'notification_pending',
          notificationStatus: 'pending',
        },
        201,
      );
    });

    await page.route('**/api/writing-projects/', async (route) => {
      if (route.request().method() === 'POST') {
        await fulfillJson(
          route,
          {
            id: '10',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'New Manuscript',
            writingType: 'manuscript',
            participantRole: 'student_author',
            status: 'active',
            versions: [],
          },
          201,
        );
        return;
      }
      await fulfillJson(route, {
        results: [
          {
            id: '2',
            projectId: '1',
            legacyProjectId: '1',
            studentId: '5',
            title: 'Thesis Chapter',
            writingType: 'thesis',
            participantRole: uploaded ? 'assigned_reviewer' : 'student_author',
            status: 'active',
            versions: [
              {
                id: '6',
                writingProjectId: '2',
                versionNumber: 1,
                draftFileName: 'chapter.docx',
                fileKind: 'word',
                status: 'feedback_available',
                feedback: [
                  {
                    id: '7',
                    writingVersionId: '6',
                    reviewerId: '3',
                    comments: 'Revise section two',
                    status: 'notification_pending',
                    annotatedFileName: 'annotated.docx',
                    notificationStatus: 'pending',
                  },
                ],
              },
            ],
          },
        ],
      });
    });
  }

  if (fullStackE2E) {
    await loginAs(page);
    await page.goto('/writing');
    await expect(page.getByRole('heading', { name: 'Writing projects', exact: true })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Writing projects' })).toBeVisible();
    await expect(page.getByLabel('Search writing projects')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create writing project' })).toHaveCount(0);
    return;
  }

  await page.goto('/writing');
  await expect(page.getByRole('heading', { name: 'Writing projects', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Thesis Chapter' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Version 1/ })).toBeVisible();

  await page.getByLabel('Writing version file').setInputFiles({
    name: 'revision.tex',
    mimeType: 'text/x-tex',
    buffer: Buffer.from('\\section{Revision}'),
  });
  await page.getByLabel('Version summary').fill('Second pass');
  await page.getByRole('button', { name: 'Upload version' }).click();
  expect(uploaded).toBe(true);
  await expect(page.getByRole('button', { name: 'Choose feedback file' })).toBeVisible();

  await page.getByLabel('Annotated file').setInputFiles({
    name: 'annotated.docx',
    mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    buffer: Buffer.from('notes'),
  });
  await page.getByLabel('Feedback comments').fill('More notes');
  await page.getByRole('button', { name: 'Submit feedback' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Feedback saved and notification recorded' }).first()).toBeVisible();
  expect(feedbackSubmitted).toBe(true);

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /Download annotated file/ }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('annotated.docx');
  await expect(page.getByRole('status').filter({ hasText: 'annotated.docx' }).first()).toBeVisible();
});
