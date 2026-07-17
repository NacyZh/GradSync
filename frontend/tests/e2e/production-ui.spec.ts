import { expect, test, type Locator, type Page } from '@playwright/test';

import { loginAs, fullStackE2E, mockAuthenticatedApi } from './api-mocks';

type LayoutBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

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
    requiredRegions: ['Current tasks', 'Task details', 'Pending reviews'],
  },
  {
    name: 'tablet-review-dark',
    width: 900,
    height: 950,
    path: '/projects/1/reviews',
    theme: 'dark',
    requiredRegions: ['Submission review', 'Inline comments'],
  },
  {
    name: 'mobile-booking-light',
    width: 390,
    height: 900,
    path: '/projects/1/resources',
    theme: 'light',
    requiredRegions: ['Resource filters', 'Resource list', 'Booking calendar'],
  },
];

const routeCases = [
  { path: '/projects/1', label: 'project dashboard' },
  { path: '/projects/1/resources', label: 'resource booking' },
  { path: '/projects/1/papers', label: 'paper library' },
  { path: '/projects/1/code', label: 'code repository' },
  { path: '/', label: 'notifications dashboard' },
  { path: '/admin/accounts', label: 'account administration' },
];

const viewportSizes = [
  { width: 1440, height: 950 },
  { width: 900, height: 950 },
  { width: 390, height: 900 },
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
      await expect(page.getByRole('region', { name: 'Selected project context' })).toHaveCount(0);

      await setTheme(page, viewport.theme);
      for (const region of viewport.requiredRegions) {
        await expect(page.locator(`[aria-label="${region}"]`).first()).toBeVisible();
      }

      const shellLandmarks = [
        page.getByRole('banner'),
        page.getByRole('complementary', { name: 'Workspace navigation' }),
      ];
      await expectVisibleLandmarksDoNotOverlap(page, shellLandmarks);

      await page.screenshot({
        path: testInfo.outputPath(`${viewport.name}.png`),
        fullPage: true,
      });
    });
  }

  for (const routeCase of routeCases) {
    for (const viewport of viewportSizes) {
      test(`${routeCase.label} has no clipped primary layout at ${viewport.width}px`, async ({ page }) => {
        await mockAuthenticatedApi(page);
        if (fullStackE2E) {
          await loginAs(page);
        }

        await page.setViewportSize(viewport);
        await page.goto(routeCase.path);
        await expect(page.getByRole('banner')).toBeVisible();
        await expect(page.getByRole('main')).toBeVisible();

        await expectPrimaryControlsStayInsideViewport(page);
        await expectNoVisibleTextOverlap(page);
        if (routeCase.path === '/projects/1') {
          await expectMembersPanelContentStaysInside(page);
        }
      });
    }
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

async function expectPrimaryControlsStayInsideViewport(page: Page) {
  const viewport = page.viewportSize();
  expect(viewport).not.toBeNull();
  const boxes = await visibleElementBoxes(
    page,
    'main button:visible, main a:visible, header button:visible, aside a:visible',
    30,
  );
  expect(boxes.length).toBeGreaterThan(0);
  for (const box of boxes) {
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual((viewport?.width ?? 0) + 1);
  }
}

async function expectNoVisibleTextOverlap(page: Page) {
  const boxes = await visibleElementBoxes(
    page,
    'main h1, main h2, main p, main label',
    24,
  );
  for (let leftIndex = 0; leftIndex < boxes.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < boxes.length; rightIndex += 1) {
      const overlapX = Math.max(0, Math.min(boxes[leftIndex].x + boxes[leftIndex].width, boxes[rightIndex].x + boxes[rightIndex].width) - Math.max(boxes[leftIndex].x, boxes[rightIndex].x));
      const overlapY = Math.max(0, Math.min(boxes[leftIndex].y + boxes[leftIndex].height, boxes[rightIndex].y + boxes[rightIndex].height) - Math.max(boxes[leftIndex].y, boxes[rightIndex].y));
      const overlapArea = overlapX * overlapY;
      expect(overlapArea).toBeLessThanOrEqual(1);
    }
  }
}

async function expectMembersPanelContentStaysInside(page: Page) {
  const panel = page.getByRole('complementary', { name: 'Members and progress' });
  await expect(panel).toBeVisible();
  const panelBox = await panel.boundingBox();
  expect(panelBox).not.toBeNull();
  const memberRows = await panel.locator('li').evaluateAll((elements) =>
    elements.map((element) => {
      const rect = element.getBoundingClientRect();
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
    }),
  );
  for (const row of memberRows) {
    expect(row.x).toBeGreaterThanOrEqual((panelBox?.x ?? 0) - 1);
    expect(row.x + row.width).toBeLessThanOrEqual((panelBox?.x ?? 0) + (panelBox?.width ?? 0) + 1);
  }
}

async function visibleElementBoxes(page: Page, selector: string, limit: number): Promise<LayoutBox[]> {
  return page.locator(selector).evaluateAll((elements, maxCount) => {
    return elements
      .filter((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return (
          style.visibility !== 'hidden' &&
          style.display !== 'none' &&
          rect.width > 0 &&
          rect.height > 0
        );
      })
      .slice(0, maxCount)
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        };
      });
  }, limit);
}
