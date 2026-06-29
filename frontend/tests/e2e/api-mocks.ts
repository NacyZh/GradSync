import type { Page, Route } from '@playwright/test';

export const currentUser = {
  id: 10,
  email: 'advisor@example.edu',
  name: 'Advisor One',
  global_role: 'advisor',
  status: 'active',
};

export const selectedProject = {
  id: 1,
  title: 'Graphene Lab',
  description: 'Research operations validation',
  status: 'active',
  memberships: [],
  current_tasks: [{ id: 11, title: 'Analyze sample', status: 'in_progress' }],
  pending_reviews: [{ target_type: 'progress_report', target_id: '21', submitted_at: '2026-06-20T00:00:00Z' }],
  upcoming_bookings: [{ id: 31, resource_id: 41, starts_at: '2026-06-27T08:00:00Z', ends_at: '2026-06-27T09:00:00Z', status: 'reserved' }],
  activity: [
    { source: 'comment', event_type: 'inline_comment.open', summary: 'Comment on progress_report 21: summary', created_at: '2026-06-25T08:00:00Z' },
    { source: 'notification', event_type: 'notification.queued', summary: 'Pending review reminder', created_at: '2026-06-25T08:05:00Z' },
  ],
};

export async function mockUnauthenticated(page: Page) {
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ status: 401, json: { message: 'Authentication required' } });
  });
}

export async function mockLogin(page: Page, user = currentUser) {
  await page.route('**/api/accounts/login/', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ json: user });
      return;
    }
    await route.fulfill({ status: 405 });
  });
  await page.route('**/api/accounts/logout/', async (route) => {
    await route.fulfill({ status: 204 });
  });
  // After login, /api/accounts/me/ returns the authenticated user.
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ json: user });
  });
}

export async function mockAuthenticatedApi(page: Page) {
  await page.route('**/api/accounts/me/', async (route) => {
    await route.fulfill({ json: currentUser });
  });
  await page.route('**/api/accounts/logout/', async (route) => {
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/projects/1/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: selectedProject });
      return;
    }
    await route.fulfill({ json: selectedProject });
  });
  await page.route('**/api/projects/1/notifications/', async (route) => {
    await route.fulfill({
      json: {
        results: [{ id: 1, subject: 'Pending review reminder', status: 'queued' }],
      },
    });
  });
}

export async function fulfillJson(route: Route, json: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
}
