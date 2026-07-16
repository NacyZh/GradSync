import { expect, test, type Page } from '@playwright/test';

import { fulfillAttachment, fulfillJson, validPdfBuffer } from './api-mocks';

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
  let liveMemberAdded = false;

  await page.route('**/api/accounts/me/', async (route) => fulfillJson(route, currentUser));
  await page.route('**/api/accounts/logout/', async (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/code-artifacts/upload-policy/', async (route) => {
    await fulfillJson(route, {
      category: 'code_archive',
      maxSizeBytes: 104857600,
      displayLabel: '100 MB',
      allowedExtensions: ['.7z', '.bz2', '.gz', '.tar', '.tgz', '.xz', '.zip'],
      contentTypes: ['application/zip', 'application/gzip', 'application/x-tar'],
    });
  });
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
      capabilities: {
        canManageProject: true,
        canEditProject: true,
        canArchiveProject: true,
        canReopenProject: false,
        canDeleteProject: false,
        canManageMembers: true,
        canCreateTasks: true,
        canUpdateTasks: true,
        deleteDisabledReason: 'Projects with research activity must be archived instead of deleted',
      },
      memberships: [
        { id: 1, projectId: 1, userId: 10, nickname: 'Advisor One', email: 'advisor@example.edu', role: 'advisor', status: 'active' },
        { id: 2, projectId: 1, userId: 12, nickname: 'Student One', email: 'student.one@example.edu', role: 'student', status: 'active' },
        ...(liveMemberAdded ? [{ id: 4, projectId: 1, userId: 14, nickname: 'Alex', email: 'alex.two@example.edu', role: 'student', status: 'active' }] : []),
      ],
      current_tasks: [],
      pending_reviews: [],
      upcoming_bookings: [],
      activity: [],
    });
  });
  await page.route('**/api/projects/1/members/', async (route) => {
    if (route.request().method() === 'POST') {
      liveMemberAdded = true;
      await fulfillJson(route, { id: 4, projectId: 1, userId: 14, nickname: 'Alex', email: 'alex.two@example.edu', role: 'student', status: 'active' }, 201);
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/projects/1/events/', async (route) => {
    await fulfillJson(route, {
      latestEventId: liveMemberAdded ? 'audit:44' : null,
      generatedAt: new Date().toISOString(),
      results: liveMemberAdded
        ? [{ id: 'audit:44', source: 'audit', eventType: 'membership.added', targetType: 'ProjectMembership', targetId: '4', summary: 'Membership added', actorId: 10, createdAt: new Date().toISOString() }]
        : [],
    });
  });
  await page.route('**/api/projects/1/members/2/', async (route) => route.fulfill({ status: 204 }));
  await page.route('**/api/library/papers/**', async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith('/api/library/papers/') && request.method() === 'POST') {
      paperUploaded = true;
      await fulfillJson(route, {
        id: 'import-platform',
        status: 'accepted',
        requestedBy: 10,
        userMessage: 'Paper imported',
        acceptedPaper: {
          id: '2',
          projectId: '1',
          title: 'Uploaded Graph Paper',
          canonicalTitle: 'Uploaded Graph Paper',
          authors: ['Ada Lovelace'],
          publicationYear: 2026,
          keywords: [],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: 'Uploaded Graph Paper.pdf',
        },
        duplicatePaper: null,
        extraction: {
          source: 'embedded_metadata',
          extractedTitle: 'Uploaded Graph Paper',
          confidence: 'high',
          failureReason: '',
        },
        duplicateDetection: null,
        failureReason: '',
        createdAt: '2026-07-06T00:00:00Z',
        updatedAt: '2026-07-06T00:00:02Z',
        completedAt: '2026-07-06T00:00:02Z',
      }, 202);
      return;
    }
    if (url.endsWith('/api/library/papers/2/download/')) {
      await fulfillAttachment(route, 'Uploaded Graph Paper.pdf', Buffer.from('%PDF-1.4 uploaded'), 'application/pdf');
      return;
    }
    if (url.endsWith('/api/library/papers/1/download/')) {
      await fulfillAttachment(route, 'Group Wide Graph Paper.pdf', Buffer.from('%PDF-1.4 group'), 'application/pdf');
      return;
    }
    if (url.endsWith('/api/library/papers/2/')) {
      await fulfillJson(route, {
        id: '2',
        projectId: '1',
        title: 'Uploaded Graph Paper',
        canonicalTitle: 'Uploaded Graph Paper',
        authors: ['Ada Lovelace'],
        publicationYear: 2026,
        keywords: [],
        visibility: 'group_wide',
        status: 'active',
        downloadAvailable: true,
        defaultDownloadFilename: 'Uploaded Graph Paper.pdf',
      });
      return;
    }
    if (url.endsWith('/api/library/papers/1/')) {
      await fulfillJson(route, {
        id: '1',
        projectId: '1',
        title: 'Group Wide Graph Paper',
        canonicalTitle: 'Group Wide Graph Paper',
        authors: ['Lin Chen'],
        publicationYear: 2025,
        keywords: ['graph'],
        visibility: 'group_wide',
        status: 'active',
        downloadAvailable: true,
        defaultDownloadFilename: 'Group Wide Graph Paper.pdf',
      });
      return;
    }
    await fulfillJson(route, {
      results: [
        {
          id: paperUploaded ? '2' : '1',
          projectId: '1',
          title: paperUploaded ? 'Uploaded Graph Paper' : 'Group Wide Graph Paper',
          canonicalTitle: paperUploaded ? 'Uploaded Graph Paper' : 'Group Wide Graph Paper',
          authors: paperUploaded ? ['Ada Lovelace'] : ['Lin Chen'],
          publicationYear: paperUploaded ? 2026 : 2025,
          keywords: paperUploaded ? [] : ['graph'],
          visibility: 'group_wide',
          status: 'active',
          downloadAvailable: true,
          defaultDownloadFilename: paperUploaded ? 'Uploaded Graph Paper.pdf' : 'Group Wide Graph Paper.pdf',
        },
      ],
      count: 1,
    });
  });
  await page.route('**/api/library/code/**', async (route) => {
    const request = route.request();
    if (request.url().includes('/download')) {
      await fulfillAttachment(route, 'uploaded.zip', Buffer.from('zip'), 'application/zip');
      return;
    }
    if (request.method() === 'POST') {
      codeUploaded = true;
      await fulfillJson(route, { id: '5', projectId: '1', name: 'Uploaded Archive', description: 'Searchable implementation archive', tags: ['python'], visibility: 'group_wide', checksumSha256: 'e'.repeat(64), archiveFileId: '12', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: codeUploaded ? '5' : '3', projectId: '1', name: codeUploaded ? 'Uploaded Archive' : 'Group Code Archive', description: 'Microscopy analysis archive', tags: ['analysis'], visibility: 'group_wide', checksumSha256: 'c'.repeat(64), archiveFileId: '9', status: 'active' }] });
  });
  await page.route('**/api/document-categories**', async (route) => {
    await fulfillJson(route, [
      { id: '1', name: 'Protocols', description: 'Lab protocols', status: 'active' },
      { id: '2', name: 'Reports', description: 'Research reports', status: 'active' },
      { id: '3', name: 'Meetings', description: 'Meeting notes', status: 'active' },
    ]);
  });
  await page.route('**/api/library/documents/**', async (route) => {
    if (route.request().url().includes('/download/')) {
      await fulfillAttachment(route, 'protocol.pdf', Buffer.from('%PDF-1.4 protocol'), 'application/pdf');
      return;
    }
    if (route.request().method() === 'POST') {
      documentUploaded = true;
      await fulfillJson(route, { id: '5', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: 'Uploaded Protocol', description: 'Shared instructions', visibility: 'group_wide', uploaderId: '10', checksumSha256: 'b'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: documentUploaded ? '5' : '4', projectId: '1', categoryId: '1', categoryName: 'Protocols', title: documentUploaded ? 'Uploaded Protocol' : 'Microscope Protocol', description: 'Calibration workflow', visibility: 'group_wide', uploaderId: '10', checksumSha256: 'a'.repeat(64), createdAt: '2026-07-03T08:00:00Z', status: 'active' }] });
  });
  await page.route('**/api/library/documents/*/download/', async (route) =>
    fulfillAttachment(route, 'protocol.pdf', Buffer.from('%PDF-1.4 protocol'), 'application/pdf'),
  );
  await page.route('**/api/writing-projects/**', async (route) => {
    if (route.request().url().includes('/versions')) {
      await route.fallback();
      return;
    }
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: '10', projectId: '1', studentId: '5', title: 'New Manuscript', writingType: 'manuscript', status: 'active', versions: [] }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: '2', projectId: '1', studentId: '5', title: 'Thesis Chapter', writingType: 'thesis', participantRole: 'assigned_reviewer', status: 'active', versions: [{ id: '6', writingProjectId: '2', versionNumber: 1, draftFileName: 'chapter.docx', fileKind: 'word', status: 'feedback_available', feedback: [{ id: '7', writingVersionId: '6', reviewerId: '3', comments: 'Revise section two', status: 'notification_pending', annotatedFileName: 'annotated.docx', notificationStatus: 'pending' }] }] }] });
  });
  await page.route('**/api/writing-projects/2/versions', async (route) => {
    await fulfillJson(route, { id: '8', writingProjectId: '2', versionNumber: 2, draftFileName: 'revision.tex', fileKind: 'latex_source', status: 'submitted', feedback: [] }, 201);
  });
  await page.route('**/api/writing-versions/6/feedback', async (route) => fulfillJson(route, { id: '9', writingVersionId: '6', reviewerId: '3', comments: 'More notes', status: 'notification_pending', notificationStatus: 'pending' }, 201));
  await page.route('**/api/teacher-feedback/7/download', async (route) =>
    fulfillAttachment(
      route,
      'annotated.docx',
      Buffer.from('notes'),
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ),
  );
  await page.route('**/api/resources/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 12, name: 'New microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.' }, 201);
      return;
    }
    await fulfillJson(route, { results: [{ id: 7, name: 'Confocal microscope', resourceType: 'Microscope', description: 'Shared imaging station', status: 'active', useInstructions: 'Submit request first.' }] });
  });
  await page.route('**/api/resource-items/', async (route) => fulfillJson(route, { results: [{ id: 41, resourceTypeId: 1, name: 'Confocal microscope', status: 'available', available: true }] }));
  await page.route('**/api/resource-types/', async (route) => fulfillJson(route, { results: [{ id: 1, name: 'Microscope', scope: 'global', fieldSchema: [], status: 'active' }] }));
  await page.route('**/api/projects/1/bookings/', async (route) => fulfillJson(route, { results: [] }));
  await page.route('**/api/bookings**', async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await fulfillJson(route, {
        id: 22,
        resourceId: body.resourceId,
        resourceName: 'Confocal microscope',
        requestedById: 10,
        startsAt: body.startsAt,
        endsAt: body.endsAt,
        quantity: body.quantity,
        origin: 'staff_direct',
        confirmationPolicy: 'approval_required',
        status: 'confirmed',
        purpose: body.purpose,
        version: 1,
      }, 201);
      return;
    }
    if (url.searchParams.get('reviewQueue') === 'true') {
      await fulfillJson(route, { results: [] });
      return;
    }
    await fulfillJson(route, { results: [] });
  });
  await page.route('**/api/projects/1/notifications/', async (route) => {
    await fulfillJson(route, { results: [{ id: 31, project_id: 1, event_type: 'teacher_feedback_available', target_type: 'TeacherFeedback', target_id: '17', subject: 'Feedback available', action_path: '/writing', status: 'retry_needed', eligible_at: '2026-07-03T09:05:00Z', last_attempt_at: '2026-07-03T09:00:00Z', retry_count: 1, failure_reason: 'SMTP provider unavailable' }] });
  });

  return {
    setAdmin() {
      currentUser = adminUser;
    },
    setAdvisor() {
      currentUser = advisorUser;
    },
    triggerMemberEvent() {
      liveMemberAdded = true;
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
    await expect(page.getByRole('listbox', { name: 'Student search results' })).toContainText('alex.two@example.edu');
    await page.getByRole('listbox', { name: 'Student search results' }).getByRole('option', { name: /alex.two@example.edu/ }).click();
    await expect(page.getByText('Member added')).toBeVisible();
  });

  await test.step('shared paper library import and download', async () => {
    await page.goto('/library/papers');
    await expect(page.getByRole('button', { name: /Select paper Group Wide Graph Paper/ })).toBeVisible();
    await expect(page.getByLabel('Paper title')).toHaveCount(0);
    await page.getByLabel('PDF file').setInputFiles({
      name: 'uploaded-paper.pdf',
      mimeType: 'application/pdf',
      buffer: validPdfBuffer('Uploaded Graph Paper'),
    });
    await page.getByRole('button', { name: 'Import PDF' }).click();
    await expect(page.getByText('Accepted: Uploaded Graph Paper')).toBeVisible();
    await page.getByRole('button', { name: /Download Uploaded Graph Paper/ }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Download started' })).toContainText('Uploaded Graph Paper.pdf');
  });

  await test.step('code archive library', async () => {
    await page.goto('/library/code');
    await expect(page.getByTestId('code-selected-detail-region').getByRole('heading', { name: 'Group Code Archive' })).toBeVisible();
    await page.getByLabel('Archive file').setInputFiles({ name: 'uploaded.zip', mimeType: 'application/zip', buffer: Buffer.from('zip') });
    await page.getByLabel('Artifact name').fill('Uploaded Archive');
    await page.getByLabel('Artifact description').fill('Searchable implementation archive');
    await page.getByRole('button', { name: 'Upload archive' }).click();
    await expect(page.getByText('Upload complete')).toBeVisible();
  });

  await test.step('document categories and document library', async () => {
    await page.goto('/library/documents');
    await expect(
      page
        .getByTestId('document-selected-detail-region')
        .getByRole('heading', { name: 'Microscope Protocol' }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Category Protocols' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await page.getByLabel('Document file').setInputFiles({ name: 'uploaded.md', mimeType: 'text/markdown', buffer: Buffer.from('# protocol') });
    await page.getByLabel('Document title').fill('Uploaded Protocol');
    await page.getByLabel('Document description').fill('Shared instructions');
    await page.getByRole('button', { name: 'Upload document' }).click();
    await expect(page.getByText('Upload complete')).toBeVisible();
  });

  await test.step('writing versions and teacher feedback notification', async () => {
    await page.goto('/writing');
    await expect(page.getByRole('heading', { name: 'Thesis Chapter' })).toBeVisible();
    await page.getByLabel('Annotated file').setInputFiles({ name: 'annotated.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: Buffer.from('notes') });
    await page.getByLabel('Feedback comments').fill('More notes');
    await page.getByRole('button', { name: 'Submit feedback' }).click();
    await expect(page.getByText('Feedback saved and notification recorded')).toBeVisible();
  });

  await test.step('laboratory resource inventory and student use', async () => {
    await page.goto('/projects/1/resources');
    await expect(page.getByRole('region', { name: 'Resource list' })).toContainText('Confocal microscope');
    const useForm = page.getByRole('form', { name: 'Submit resource use' });
    await useForm.getByLabel('Start').fill('2099-01-02T09:00');
    await useForm.getByLabel('End').fill('2099-01-02T10:00');
    await useForm.getByLabel('Purpose').fill('Use for calibration');
    await useForm.getByRole('button', { name: 'Record use' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Use recorded' }).first()).toBeVisible();
  });

  await test.step('notification degradation status', async () => {
    await page.goto('/projects/1');
    await expect(page.getByRole('region', { name: 'Notifications', exact: true })).toContainText('Feedback available');
    await expect(page.getByRole('alert')).toContainText('SMTP provider unavailable');
  });
});

test('project dashboard refreshes from project events without full reload', async ({ page }) => {
  const auth = await mockCollaborationApi(page);

  await page.goto('/projects/1');
  await expect(page.getByRole('region', { name: 'Project members' })).not.toContainText('alex.two@example.edu');
  auth.triggerMemberEvent();
  await expect(page.getByRole('region', { name: 'Project members' })).toContainText('alex.two@example.edu', { timeout: 7000 });
});
