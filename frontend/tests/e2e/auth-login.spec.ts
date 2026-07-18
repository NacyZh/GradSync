import { expect, test } from '@playwright/test';

import { currentUser, fulfillJson } from './api-mocks';

test.describe('authentication', () => {
  test('unauthenticated visitor is redirected to login from every protected route', async ({ page }) => {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, { message: 'Authentication required' }, 401);
    });

    const protectedPaths = ['/projects/1', '/projects/new', '/projects/1/reports', '/projects/1/reviews', '/resources'];
    for (const path of protectedPaths) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login/);
      await expect(page.getByRole('heading', { name: 'GradSync' })).toBeVisible();
      await expect(page.getByLabel('Email')).toBeVisible();
      await expect(page.getByLabel('Password')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
    }
  });

  test('login page redirects to home when already authenticated', async ({ page }) => {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, currentUser);
    });

    await page.goto('/login');
    await expect(page).toHaveURL('/');
    await expect(page.getByText(currentUser.name)).toBeVisible();
  });

  test('user signs in with valid credentials and reaches home page', async ({ page }) => {
    let loginAttempts = 0;
    await page.route('**/api/accounts/me/', async (route) => {
      if (loginAttempts > 0) {
        await fulfillJson(route, currentUser);
        return;
      }
      await fulfillJson(route, { message: 'Authentication required' }, 401);
    });

    await page.route('**/api/accounts/login/', async (route) => {
      if (route.request().method() === 'POST') {
        loginAttempts += 1;
        await fulfillJson(route, currentUser);
        return;
      }
      await fulfillJson(route, {}, 405);
    });

    await page.route('**/api/projects/', async (route) => {
      await fulfillJson(route, { results: [] });
    });

    await page.goto('/login');
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeDisabled();

    await page.getByLabel('Email').fill(currentUser.email);
    await page.getByLabel('Password').fill('correct-password');
    await expect(page.getByRole('button', { name: 'Sign in' })).not.toBeDisabled();

    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { name: 'Advisor workspace' })).toBeVisible();
    await expect(page.getByText(currentUser.name)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  });

  test('login layout is centered, full-viewport, aligned, and password toggle is stable', async ({ page }) => {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, { message: 'Authentication required' }, 401);
    });

    for (const viewport of [
      { width: 390, height: 844 },
      { width: 900, height: 950 },
      { width: 1440, height: 950 },
    ]) {
      await page.setViewportSize(viewport);
      await page.goto('/login');

      const screen = page.locator('.login-screen');
      const card = page.locator('.login-card');
      const email = page.getByLabel('Email');
      const password = page.getByLabel('Password');
      const toggle = page.getByRole('button', { name: 'Show password' });
      const submit = page.getByRole('button', { name: 'Sign in' });

      await expect(screen).toBeVisible();
      await expect(card).toBeVisible();
      await expect(toggle).toBeVisible();
      await expect(submit).toBeVisible();
      await expect(screen).not.toHaveCSS('background-image', /images\.unsplash\.com/);

      const screenBox = await screen.boundingBox();
      const cardBox = await card.boundingBox();
      const emailBox = await email.boundingBox();
      const passwordBox = await password.boundingBox();
      const submitBefore = await submit.boundingBox();

      expect(screenBox?.width).toBeGreaterThanOrEqual(viewport.width - 1);
      expect(screenBox?.height).toBeGreaterThanOrEqual(viewport.height - 1);
      expect(cardBox).not.toBeNull();
      expect(emailBox).not.toBeNull();
      expect(passwordBox).not.toBeNull();
      expect(Math.abs((emailBox?.x ?? 0) - (passwordBox?.x ?? 0))).toBeLessThanOrEqual(2);
      expect(Math.abs((emailBox?.width ?? 0) - (passwordBox?.width ?? 0))).toBeLessThanOrEqual(2);

      const cardCenter = (cardBox?.x ?? 0) + (cardBox?.width ?? 0) / 2;
      expect(Math.abs(cardCenter - viewport.width / 2)).toBeLessThanOrEqual(24);

      await toggle.click();
      await expect(page.getByLabel('Password')).toHaveAttribute('type', 'text');
      const submitAfter = await submit.boundingBox();
      expect(Math.abs((submitBefore?.y ?? 0) - (submitAfter?.y ?? 0))).toBeLessThanOrEqual(1);
    }
  });

  test('login fails with generic error on invalid credentials', async ({ page }) => {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, { message: 'Authentication required' }, 401);
    });

    await page.route('**/api/accounts/login/', async (route) => {
      if (route.request().method() === 'POST') {
        await fulfillJson(route, { message: 'Invalid email or password' }, 400);
        return;
      }
      await fulfillJson(route, {}, 405);
    });

    await page.goto('/login');
    await page.getByLabel('Email').fill('wrong@example.edu');
    await page.getByLabel('Password').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Invalid email or password')).toBeVisible();
    // Should remain on login page after failed attempt
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  });

  test('user can sign out and is returned to login', async ({ page }) => {
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, currentUser);
    });
    await page.route('**/api/accounts/logout/', async (route) => {
      await fulfillJson(route, {}, 204);
    });
    await page.route('**/api/projects/', async (route) => {
      await fulfillJson(route, { results: [] });
    });

    await page.goto('/');
    await expect(page.getByText(currentUser.name)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();

    // After clicking sign out, redirect /api/accounts/me/ to 401
    await page.route('**/api/accounts/me/', async (route) => {
      await fulfillJson(route, { message: 'Authentication required' }, 401);
    });

    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page).toHaveURL('/login');
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  });
});
