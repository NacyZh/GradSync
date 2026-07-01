import { expect, type Page, type Route } from '@playwright/test';

export const fullStackE2E = process.env.GRADSYNC_E2E_MODE === 'fullstack';

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
  current_tasks: [{
    id: 11,
    title: 'Analyze sample',
    status: 'in_progress',
    priority: 'high',
    deadline_at: '2026-06-30T08:00:00Z',
    assignee_id: 12,
    children: [{ id: 12, title: 'Draft chart', status: 'not_started', priority: 'high', assignee_id: 12 }],
  }],
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
  if (fullStackE2E) {
    return;
  }
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
        results: [{ id: 1, event_type: 'pending_review', target_type: 'progress_report', target_id: '21', subject: 'Pending review reminder', action_path: '/projects/1/reviews', status: 'queued', eligible_at: '2026-06-25T08:05:00Z' }],
      },
    });
  });
  await page.route('**/api/projects/1/tasks/11/', async (route) => {
    await fulfillJson(route, { id: 11, title: 'Analyze sample', status: 'completed', priority: 'high' });
  });
  await page.route('**/api/projects/1/tasks/12/', async (route) => {
    await fulfillJson(route, { id: 12, title: 'Draft chart', status: 'completed', priority: 'high' });
  });
  await page.route('**/api/projects/1/tasks/', async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { id: 12, title: 'New task', status: 'not_started', priority: 'normal' }, 201);
      return;
    }
    await fulfillJson(route, { results: selectedProject.current_tasks });
  });
}

export async function fulfillJson(route: Route, json: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(json) });
}

export async function loginAs(
  page: Page,
  email = 'advisor@example.edu',
  password = 'password123',
) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes('/api/accounts/login/') && response.status() === 200,
    ),
    page.getByRole('button', { name: 'Sign in' }).click(),
  ]);
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
}
