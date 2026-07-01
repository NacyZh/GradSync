import { expect, test, type Locator, type Page } from '@playwright/test';

import { loginAs, fullStackE2E, mockAuthenticatedApi } from './api-mocks';

type ViewportCase = {
  name: string;
  width: number;
  height: number;
  path: string;
  theme: 'light' | 'dark';
  requiredRegions: string[];
};

const workspaceCases: ViewportCase[] = [
  {
    name: 'desktop-dashboard-light',
    width: 1440,
    height: 950,
    path: '/projects/1',
    theme: 'light',
    requiredRegions: ['Selected project context', 'Current tasks', 'Task details', 'Activity'],
  },
  {
    name: 'tablet-review-dark',
    width: 900,
    height: 950,
    path: '/projects/1/reviews',
    theme: 'dark',
    requiredRegions: ['Selected project context', 'Submission review', 'Inline comments'],
  },
  {
    name: 'mobile-booking-light',
    width: 390,
    height: 900,
    path: '/projects/1/resources',
    theme: 'light',
    requiredRegions: ['Selected project context', 'Resource filters', 'Resource list', 'Booking calendar'],
  },
];

test.describe('production workspace layout', () => {
  for (const viewport of workspaceCases) {
    test(`${viewport.name} keeps shell regions visible without overlap`, async ({ page }, testInfo) => {
      await mockAuthenticatedApi(page);
      if (fullStackE2E) {
        await loginAs(page);
      }

      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(viewport.path);
      await expect(page.getByRole('banner')).toBeVisible();
      await expect(page.getByRole('main')).toBeVisible();
      await expect(page.getByRole('complementary', { name: 'Workspace navigation' })).toBeVisible();
      await expect(page.getByRole('region', { name: 'Selected project context' })).toBeVisible();

      await setTheme(page, viewport.theme);
      for (const region of viewport.requiredRegions) {
        await expect(page.locator(`[aria-label="${region}"]`).first()).toBeVisible();
      }

      await expectVisibleLandmarksDoNotOverlap(page, [
        page.getByRole('banner'),
        page.getByRole('complementary', { name: 'Workspace navigation' }),
        page.getByRole('region', { name: 'Selected project context' }),
      ]);

      await page.screenshot({
        path: testInfo.outputPath(`${viewport.name}.png`),
        fullPage: true,
      });
    });
  }
});

async function setTheme(page: Page, theme: 'light' | 'dark') {
  const html = page.locator('html');
  const current = await html.getAttribute('data-theme');
  if (current !== theme) {
    await page.getByRole('button', { name: `Switch to ${theme} theme` }).click();
  }
  await expect(html).toHaveAttribute('data-theme', theme);
}

async function expectVisibleLandmarksDoNotOverlap(page: Page, locators: Locator[]) {
  const boxes = [];
  for (const locator of locators) {
    const box = await locator.boundingBox();
    expect(box).not.toBeNull();
    if (box) boxes.push(box);
  }

  const viewport = page.viewportSize();
  expect(viewport).not.toBeNull();
  for (const box of boxes) {
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual((viewport?.width ?? 0) + 1);
  }

  for (let leftIndex = 0; leftIndex < boxes.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < boxes.length; rightIndex += 1) {
      const overlapX = Math.max(0, Math.min(boxes[leftIndex].x + boxes[leftIndex].width, boxes[rightIndex].x + boxes[rightIndex].width) - Math.max(boxes[leftIndex].x, boxes[rightIndex].x));
      const overlapY = Math.max(0, Math.min(boxes[leftIndex].y + boxes[leftIndex].height, boxes[rightIndex].y + boxes[rightIndex].height) - Math.max(boxes[leftIndex].y, boxes[rightIndex].y));
      expect(overlapX * overlapY).toBe(0);
    }
  }
}
