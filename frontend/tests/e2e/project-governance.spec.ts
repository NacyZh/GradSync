import { expect, test } from '@playwright/test';

import { fulfillJson, fullStackE2E, mockAuthenticatedApi } from './api-mocks';

test('project governance controls follow server capabilities', async ({ page }) => {
  test.skip(fullStackE2E, 'mock-owned capability matrix is covered in the mocked stage');
  await mockAuthenticatedApi(page);
  await page.route('**/api/projects/1/', async (route) => {
    await fulfillJson(route, {
      id: 1,
      title: 'Governed project',
      description: '',
      status: 'active',
      governanceState: 'hold',
      governanceHoldReason: 'owner_ineligible',
      memberships: [],
      current_tasks: [],
      pending_reviews: [],
      capabilities: {
        canViewProject: true,
        canSuperviseGovernance: true,
        canManageProject: false,
        canManageMembers: false,
        canManageCollaborators: false,
        canCreateTasks: false,
        canUpdateTasks: false,
      },
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/projects/1');

  await expect(page.getByText(/Project governance hold/).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Add/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Delete project/ })).toHaveCount(0);
});
