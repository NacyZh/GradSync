import { expect, test } from '@playwright/test';

import { fullStackE2E, loginAs, mockLogin } from './api-mocks';

const adminUser = {
  id: 1,
  email: 'admin@gradsync.local',
  name: 'Admin User',
  global_role: 'admin',
  status: 'active',
};

const healthSnapshot = {
  generatedAt: '2026-07-29T08:00:00Z',
  windowDays: 30,
  longBlockedDays: 7,
  summary: {
    activeProjects: 2,
    overdueProjects: 1,
    overdueProjectRate: 50,
    longBlockedTasks: 1,
    missingReports: 2,
    governanceHolds: 1,
    resourceConflicts: 3,
    notificationFailures: 2,
    notificationFailureRate: 25,
  },
  projects: [{
    projectId: 1,
    title: 'Delayed imaging study',
    advisorName: 'Advisor User',
    endsOn: '2026-07-20',
    overdue: true,
    openTaskCount: 6,
    overdueTaskCount: 3,
    longBlockedTaskCount: 1,
    missingReportCount: 2,
    governanceState: 'hold',
    governanceHoldReason: 'manual_correction',
    resourceConflictCount: 3,
    notificationFailureCount: 2,
    healthScore: 18,
    healthLevel: 'critical',
    actionPath: '/projects/1',
  }],
  blockedTasks: [{
    taskId: 11,
    title: 'Repair image pipeline',
    projectId: 1,
    projectTitle: 'Delayed imaging study',
    blockedSince: '2026-07-20T08:00:00Z',
    blockedDays: 9,
    deadlineAt: '2026-07-25T08:00:00Z',
    actionPath: '/projects/1',
  }],
  missingReports: [],
  governanceHolds: [],
  trend: Array.from({ length: 14 }, (_, index) => ({
    date: `2026-07-${String(16 + index).padStart(2, '0')}`,
    resourceConflicts: index === 13 ? 3 : 0,
    notificationFailures: index === 12 ? 2 : 0,
  })),
};

test.beforeEach(async ({ page }) => {
  if (fullStackE2E) {
    await loginAs(page, 'admin@gradsync.local');
    return;
  }
  await mockLogin(page, adminUser);
  await page.route('**/api/admin/project-health/', async (route) => {
    await route.fulfill({ json: healthSnapshot });
  });
});

for (const viewport of [
  { width: 390, height: 900 },
  { width: 1440, height: 950 },
]) {
  test(`administrator health console remains operable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/admin/health');

    await expect(page.getByRole('heading', { name: 'Project health operations' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Cross-project health' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Project risk ranking' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Operations failure trend' })).toBeVisible();
    await expect(page.getByRole('link', { name: fullStackE2E ? 'Graphene Lab' : 'Delayed imaging study' }).first()).toBeVisible();

    const main = page.getByRole('main');
    const overflow = await main.evaluate((element) => element.scrollWidth - element.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}
