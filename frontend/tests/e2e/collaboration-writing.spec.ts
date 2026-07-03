import { expect, test } from '@playwright/test';

import { fulfillJson, mockAuthenticatedApi } from './api-mocks';

test('writing project feedback flow is reachable', async ({ page }) => {
  await mockAuthenticatedApi(page);
  let uploaded = false;
  let feedbackSubmitted = false;

  await page.route('**/api/teacher-feedback/7/download', async (route) => {
    await fulfillJson(route, { filename: 'annotated.docx', deliveryMode: 'direct_response' });
  });

  await page.route('**/api/writing-projects/2/versions', async (route) => {
    uploaded = true;
    await fulfillJson(route, {
      id: '8',
      writingProjectId: '2',
      versionNumber: 2,
      draftFileName: 'revision.tex',
      fileKind: 'latex_source',
      status: 'submitted',
      feedback: [],
    }, 201);
  });

  await page.route('**/api/writing-versions/6/feedback', async (route) => {
    feedbackSubmitted = true;
    await fulfillJson(route, {
      id: '9',
      writingVersionId: '6',
      reviewerId: '3',
      comments: 'More notes',
      status: 'notification_pending',
      notificationStatus: 'pending',
    }, 201);
  });

  await page.route('**/api/projects/1/writing-projects/**', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, {
        id: '10',
        projectId: '1',
        studentId: '5',
        title: 'New Manuscript',
        writingType: 'manuscript',
        status: 'active',
        versions: [],
      }, 201);
      return;
    }
    await fulfillJson(route, {
      results: [{
        id: '2',
        projectId: '1',
        studentId: '5',
        title: 'Thesis Chapter',
        writingType: 'thesis',
        status: 'active',
        versions: [{
          id: '6',
          writingProjectId: '2',
          versionNumber: 1,
          draftFileName: 'chapter.docx',
          fileKind: 'word',
          status: 'feedback_available',
          feedback: [{
            id: '7',
            writingVersionId: '6',
            reviewerId: '3',
            comments: 'Revise section two',
            status: 'notification_pending',
            annotatedFileName: 'annotated.docx',
            notificationStatus: 'pending',
          }],
        }],
      }],
    });
  });

  await page.goto('/projects/1/writing');
  await expect(page.getByRole('heading', { name: 'Writing projects' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Thesis Chapter' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Version 1/ })).toBeVisible();

  await page.getByLabel('Writing version file').setInputFiles({
    name: 'revision.tex',
    mimeType: 'text/x-tex',
    buffer: Buffer.from('\\section{Revision}'),
  });
  await page.getByLabel('Version summary').fill('Second pass');
  await page.getByRole('button', { name: 'Upload version' }).click();
  await expect(page.getByText('Version uploaded')).toBeVisible();
  expect(uploaded).toBe(true);

  await page.getByLabel('Annotated file').setInputFiles({
    name: 'annotated.docx',
    mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    buffer: Buffer.from('notes'),
  });
  await page.getByLabel('Feedback comments').fill('More notes');
  await page.getByRole('button', { name: 'Submit feedback' }).click();
  await expect(page.getByText('Feedback saved and notification recorded')).toBeVisible();
  expect(feedbackSubmitted).toBe(true);

  await page.getByRole('button', { name: /Download annotated file/ }).click();
  await expect(page.getByText(/annotated.docx/)).toBeVisible();
});
