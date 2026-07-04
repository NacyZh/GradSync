import { expect, test, type Page } from '@playwright/test';

import { fulfillJson } from './api-mocks';

const advisorUser = {
  id: 10,
  email: 'advisor@example.edu',
  name: 'Advisor One',
  global_role: 'advisor',
  status: 'active',
};

const adminUser = {
  ...advisorUser,
  email: 'admin@example.edu',
  name: 'Admin One',
  global_role: 'admin',
};

async function mockCollaborationApi(page: Page) {
  let currentUser = advisorUser;
  let paperUploaded = false;
  let codeUploaded = false;
  let documentUploaded = false;

  await page.route('**/api/accounts/me/', async (route) => fulfillJson(route, currentUser));
  await page.route('**/api/accounts/logout/', async (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/accounts/register/', async (route) => {
    await fulfillJson(route, { email: 'student@example.com', status: 'pending_email_verification', requestedRole: 'student' }, 202);
  });
  await page.route('**/api/accounts/verify-email/', async (route) => {
    await fulfillJson(route, { id: 15, email: 'student@example.com', name: 'Student One', global_role: 'student', status: 'active' });
  });
  await page.route('**/api/accounts/admin/role-activations/', async (route) => {
    await fulfillJson(route, [{ id: 1, status: 'pending', requestedRole: 'teacher', activationSource: 'administrator_approval', createdAt: '2026-07-03T00:00:00Z', user: { id: 20, email: 'teacher@example.edu', name: 'Teacher One', global_role: 'advisor', status: 'pending_role_activation' } }]);
  });
  await page.route('**/api/accounts/admin/role-activations/1/', async (route) => {
    await fulfillJson(route, { id: 1, status: 'approved', requestedRole: 'teacher', user: { id: 20, email: 'teacher@example.edu', name: 'Teacher One', global_role: 'advisor', status: 'active' } });
  });
  await page.route('**/api/accounts/students/?**', async (route) => {
    await fulfillJson(route, [
      { id: 12, nickname: 'Student One', email: 'student.one@example.edu', degreeType: 'masters', label: 'Student One <student.one@example.edu>' },
      { id: 14, nickname: 'Alex', email: 'alex.two@example.edu', degreeType: 'doctoral', label: 'Alex <alex.two@example.edu>' },
    ]);
  });
  await page.route('**/api/projects/1/', async (route) => {
    await fulfillJson(route, {
      id: 1,
      title: 'Graphene Lab',
      description: 'Research operations validation',
      status: 'active',
      memberships: [
        { id: 1, projectId: 1, userId: 10, nickname: 'Advisor One', email: 'advisor@example.edu', role: 'advisor', status: 'active' },
        { id: 2, projectId: 1, userId: 12, nickname: 'Student One', email: 'student.one@example.edu', role: 'student', status: 'active' },
      ],
      current_tasks: [],
      pending_reviews: [],
      upcoming_bookings: [],
      activity: [],
    });
  });
  await page.route('**/api/projects/1/members/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 4, projectId: 1, userId: 14, nickname: 'Alex', email: 'alex.two@example.edu', role: 'student', status: 'active' }, 201);
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/projects/1/members/2/', async (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/projects/1/papers/**', async (route) => {
    const request = route.request();
    if (request.method() === 'POST' && request.url().includes('/download/')) {
      await fulfillJson(route, { filename: 'uploaded-paper.pdf', deliveryMode: 'direct_response' });
      return;
    }
    if (request.method() === 'POST') {
      paperUploaded = true;
      await fulfillJson(route, { id: '2', projectId: '1', title: 'Uploaded Graph Paper', authors: ['Ada Lovelace'], publicationYear: 2026, visibility: 'project_members', status: 'active', attachments: [{ id: '12', filename: 'uploaded-paper.pdf', checksumSha256: 'b'.repeat(64), status: 'active' }] }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: paperUploaded ? '2' : '1', projectId: '1', title: paperUploaded ? 'Uploaded Graph Paper' : 'Group Wide Graph Paper', authors: ['Lin Chen'], publicationYear: 2025, visibility: paperUploaded ? 'project_members' : 'group_wide', status: 'active', attachments: [{ id: '11', filename: paperUploaded ? 'uploaded-paper.pdf' : 'graph.pdf', checksumSha256: 'a'.repeat(64), status: 'active' }] }] });
  });
  await page.route('**/api/projects/1/code-artifacts/**', async (route) => {
    const request = route.request();
    if (request.url().includes('/download')) {
      await fulfillJson(route, { filename: 'uploaded.zip', deliveryMode: 'direct_response' });
      return;
    }
    if (request.method() === 'POST') {
      codeUploaded = true;
      await fulfillJson(route, { id: '5', projectId: '1', name: 'Uploaded Archive', description: 'Searchable implementation archive', tags: ['python'], visibility: 'project_members', checksumSha256: 'e'.repeat(64), archiveFileId: '12', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: codeUploaded ? '5' : '3', projectId: '1', name: codeUploaded ? 'Uploaded Archive' : 'Group Code Archive', description: 'Microscopy analysis archive', tags: ['analysis'], visibility: codeUploaded ? 'project_members' : 'group_wide', checksumSha256: 'c'.repeat(64), archiveFileId: '9', status: 'active' }] });
  });
  await page.route('**/api/code-artifacts/*/download', async (route) => fulfillJson(route, { filename: 'uploaded.zip', deliveryMode: 'direct_response' }));
  await page.route('**/api/document-categories**', async (route) => {
    await fulfillJson(route, [
      { id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' },
      { id: '2', name: 'Reports', description: 'Research reports', status: 'active' },
      { id: '3', name: 'Meetings', description: 'Meeting notes', status: 'active' },
    ]);
  });
  await page.route('**/api/projects/1/documents**', async (route) => {
    if (route.request().method() === 'POST') {
      documentUploaded = true;
      await fulfillJson(route, { id: '5', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: 'Uploaded Protocol', description: 'Shared instructions', visibility: 'project_members', uploaderId: '10', checksumSha256: 'b'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: documentUploaded ? '5' : '4', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: documentUploaded ? 'Uploaded Protocol' : 'Microscope Protocol', description: 'Calibration workflow', visibility: documentUploaded ? 'project_members' : 'group_wide', uploaderId: '10', checksumSha256: 'a'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }] });
  });
  await page.route('**/api/documents/*/download', async (route) => fulfillJson(route, { filename: 'protocol.pdf', deliveryMode: 'direct_response' }));
  await page.route('**/api/projects/1/writing-projects/**', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: '10', projectId: '1', studentId: '5', title: 'New Manuscript', writingType: 'manuscript', status: 'active', versions: [] }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: '2', projectId: '1', studentId: '5', title: 'Thesis Chapter', writingType: 'thesis', status: 'active', versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, draftFileName: 'chapter.docx', fileKind: 'word', status: 'feedback_available', feedback: [{ id: '7', writingVersionId: '6', reviewerId: '3', comments: 'Revise section two', status: 'notification_pending', annotatedFileName: 'annotated.docx', notificationStatus: 'pending' }] }] }] });
  });
  await page.route('**/api/writing-projects/2/versions', async (route) => fulfillJson(route, { id: '8', writingProjectId: '2', versionNumber: 2, draftFileName: 'revision.tex', fileKind: 'latex_source', status: 'submitted', feedback: [] }, 201));
  await page.route('**/api/writing-versions/6/feedback', async (route) => fulfillJson(route, { id: '9', writingVersionId: '6', reviewerId: '3', comments: 'More notes', status: 'notification_pending', notificationStatus: 'pending' }, 201));
  await page.route('**/api/teacher-feedback/7/download', async (route) => fulfillJson(route, { filename: 'annotated.docx', deliveryMode: 'direct_response' }));
  await page.route('**/api/resources/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 12, name: 'New microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.', useSubmissions: [] }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: 7, name: 'Confocal microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.', useSubmissions: [{ id: 21, resourceId: 7, studentId: 15, studentName: 'Student One', submissionType: 'request', details: 'Image samples', status: 'pending' }] }] });
  });
  await page.route('**/api/resource-items/', async (route) => fulfillJson(route, { results: [{ id: 41, resourceTypeId: 1, name: 'Confocal microscope', status: 'available', available: true }] }));
  await page.route('**/api/resource-types/', async (route) => fulfillJson(route, { results: [{ id: 1, name: 'Microscope', scope: 'global', fieldSchema: [], status: 'active' }] }));
  await page.route('**/api/projects/1/bookings/', async (route) => fulfillJson(route, { results: [] }));
  await page.route('**/api/resources/7/use-submissions/', async (route) => fulfillJson(route, { id: 22, resourceId: 7, studentId: 10, submissionType: 'request', details: 'Use for calibration', status: 'pending' }, 201));
  await page.route('**/api/resource-use-submissions/21/', async (route) => fulfillJson(route, { id: 21, resourceId: 7, studentId: 15, studentName: 'Student One', submissionType: 'request', details: 'Image samples', status: 'confirmed', decisionNote: 'Approved' }));
  await page.route('**/api/projects/1/notifications/', async (route) => {
    await fulfillJson(route, { results: [{ id: 31, project_id: 1, event_type: 'teacher_feedback_available', target_type: 'TeacherFeedback', target_id: '17', subject: 'Feedback available', action_path: '/projects/1/writing', status: 'retry_needed', eligible_at: '2026-07-03T09:05:00Z', last_attempt_at: '2026-07-03T09:00:00Z', retry_count: 1, failure_reason: 'SMTP provider unavailable' }] });
  });

  return {
    setAdmin() {
      currentUser = adminUser;
    },
    setAdvisor() {
      currentUser = advisorUser;
    },
  };
}

test('quickstart smoke covers all collaboration scenarios', async ({ page }) => {
  const auth = await mockCollaborationApi(page);

  await test.step('registration and elevated role activation', async () => {
    await page.goto('/register');
    await page.getByLabel('Email').fill('student@example.com');
    await page.getByLabel('Nickname').fill('Student One');
    await page.getByLabel('Password').fill('StrongPass1!');
    await page.getByRole('button', { name: 'Register' }).click();
    await expect(page.getByText('Verification email sent')).toBeVisible();
    await page.getByLabel('Verification code').fill('123456');
    await page.getByRole('button', { name: 'Verify email' }).click();
    await expect(page.getByText('Email verified')).toBeVisible();

    auth.setAdmin();
    await page.goto('/admin/role-activations');
    await expect(page.getByText('teacher@example.edu')).toBeVisible();
    await page.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText('Activation updated')).toBeVisible();
    auth.setAdvisor();
  });

  await test.step('project membership by nickname', async () => {
    await page.goto('/projects/1');
    await page.getByLabel('Student nickname').fill('Alex');
    await expect(page.getByText('alex.two@example.edu')).toBeVisible();
    await page.getByText('alex.two@example.edu').click();
    await expect(page.getByText('Member added')).toBeVisible();
  });

  await test.step('paper library visibility upload and download', async () => {
    await page.goto('/projects/1/papers');
    await expect(page.getByRole('heading', { name: 'Group Wide Graph Paper' })).toBeVisible();
    await page.getByLabel('PDF file').setInputFiles({ name: 'uploaded-paper.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') });
    await page.getByLabel('Paper title').fill('Uploaded Graph Paper');
    await page.getByLabel('Authors').fill('Ada Lovelace');
    await page.getByRole('button', { name: 'Upload paper' }).click();
    await expect(page.getByText('Upload complete')).toBeVisible();
    await page.getByRole('button', { name: /Download/ }).click();
    await expect(page.getByText(/uploaded-paper.pdf/)).toBeVisible();
  });

  await test.step('code archive library', async () => {
    await page.goto('/projects/1/code');
    await expect(page.getByRole('heading', { name: 'Group Code Archive' })).toBeVisible();
    await page.getByLabel('Archive file').setInputFiles({ name: 'uploaded.zip', mimeType: 'application/zip', buffer: Buffer.from('zip') });
    await page.getByLabel('Artifact name').fill('Uploaded Archive');
    await page.getByLabel('Artifact description').fill('Searchable implementation archive');
    await page.getByRole('button', { name: 'Upload archive' }).click();
    await expect(page.getByText('Upload complete')).toBeVisible();
  });

  await test.step('document categories and document library', async () => {
    await page.goto('/projects/1/documents');
    await expect(page.getByRole('heading', { name: 'Microscope Protocol' })).toBeVisible();
    await page.getByLabel('Document file').setInputFiles({ name: 'uploaded.md', mimeType: 'text/markdown', buffer: Buffer.from('# protocol') });
    await page.getByLabel('Document title').fill('Uploaded Protocol');
    await page.getByLabel('Document category').selectOption('1');
    await page.getByLabel('Document description').fill('Shared instructions');
    await page.getByRole('button', { name: 'Upload document' }).click();
    await expect(page.getByText('Upload complete')).toBeVisible();
  });

  await test.step('writing versions and teacher feedback notification', async () => {
    await page.goto('/projects/1/writing');
    await expect(page.getByRole('heading', { name: 'Thesis Chapter' })).toBeVisible();
    await page.getByLabel('Annotated file').setInputFiles({ name: 'annotated.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: Buffer.from('notes') });
    await page.getByLabel('Feedback comments').fill('More notes');
    await page.getByRole('button', { name: 'Submit feedback' }).click();
    await expect(page.getByText('Feedback saved and notification recorded')).toBeVisible();
  });

  await test.step('laboratory resource inventory and student use', async () => {
    await page.goto('/projects/1/resources');
    await expect(page.getByRole('region', { name: 'Resource list' })).toContainText('Confocal microscope');
    await page.getByLabel('Use details').fill('Use for calibration');
    await page.getByRole('button', { name: 'Submit use request' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Use submission pending' }).first()).toBeVisible();
  });

  await test.step('notification degradation status', async () => {
    await page.goto('/projects/1');
    await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText('Feedback available');
    await expect(page.getByRole('alert')).toContainText('SMTP provider unavailable');
  });
});
