/**
 * P5 redesign navigation coverage.
 *
 * Uses strict fixtures so null/undefined selector errors fail this redesign gate.
 */
import type { Page } from '@playwright/test';
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './strict-fixtures';

const ANALYZE_TOGGLE = '#navbar .dropdown-toggle:has-text("Analyze")';
const ROUTE_LIST = [
  ROUTES.HOME,
  ROUTES.WORKOUT_PLAN,
  ROUTES.WORKOUT_LOG,
  ROUTES.WEEKLY_SUMMARY,
  ROUTES.SESSION_SUMMARY,
  ROUTES.PROGRESSION,
  ROUTES.VOLUME_SPLITTER,
] as const;

async function openAnalyzeDropdown(page: Page): Promise<void> {
  const analyzeToggle = page.locator(ANALYZE_TOGGLE);
  await expect(analyzeToggle).toBeVisible();
  await analyzeToggle.click();
  await expect(page.locator('#navbar .dropdown-menu.show')).toBeVisible();
}

async function openMobileNavbar(page: Page): Promise<void> {
  const collapse = page.locator('#navbarNav');
  const toggle = page.locator('#navbar .navbar-toggler');

  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(collapse).toHaveClass(/show/);
}

function waitForModalEvent(page: Page, selector: string, eventName: string): Promise<void> {
  return page.evaluate(
    ({ selector, eventName }) =>
      new Promise<void>((resolve) => {
        const modal = document.querySelector(selector);
        if (!modal) {
          resolve();
          return;
        }

        modal.addEventListener(eventName, () => resolve(), { once: true });
      }),
    { selector, eventName },
  );
}

test.describe('P5 navbar dropdown and backup trigger', () => {
  test('top-level nav order matches the redesigned workflow', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    const labels = await page.locator('#navbarNav > ul.navbar-nav').first().evaluate((navList) =>
      Array.from(navList.children).map((item) => {
        const link = item.querySelector(':scope > .nav-link');
        return (link?.textContent || '').trim().replace(/\s+/g, ' ');
      })
    );

    expect(labels).toEqual(['Plan', 'Log', 'Analyze', 'Progress', 'Distribute', 'Backup']);
  });

  test('Analyze dropdown opens and contains Weekly and Session links', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await openAnalyzeDropdown(page);

    const weekly = page.locator(SELECTORS.NAV_WEEKLY_SUMMARY);
    const session = page.locator(SELECTORS.NAV_SESSION_SUMMARY);
    await expect(weekly).toBeVisible();
    await expect(session).toBeVisible();
    await expect(weekly).toContainText('Weekly');
    await expect(session).toContainText('Session');
  });

  test('Backup trigger targets the global Program Library modal', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    const backup = page.locator(SELECTORS.NAV_BACKUP);
    await expect(backup).toBeVisible();
    await expect(backup).toHaveAttribute('data-bs-toggle', 'modal');
    await expect(backup).toHaveAttribute('data-bs-target', '#programLibraryModal');
  });

  test('Backup opens Program Library modal from every page', async ({ page }) => {
    for (const route of ROUTE_LIST) {
      await page.goto(route);
      await waitForPageReady(page);

      const modalShown = waitForModalEvent(page, '#programLibraryModal', 'shown.bs.modal');
      await page.locator(SELECTORS.NAV_BACKUP).click();

      const modal = page.locator('#programLibraryModal');
      await modalShown;
      await expect(modal).toHaveClass(/show/);
      await expect(modal).toBeVisible();
      await expect(modal.locator('#backup-list')).toBeVisible();

      const modalHidden = waitForModalEvent(page, '#programLibraryModal', 'hidden.bs.modal');
      await modal.locator('.btn-close').click();
      await modalHidden;
      await expect(modal).not.toBeVisible();
    }
  });

  test('mobile Analyze dropdown expands inline and links navigate', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await openMobileNavbar(page);
    await openAnalyzeDropdown(page);

    const analyzeToggle = page.locator(ANALYZE_TOGGLE);
    const dropdownMenu = page.locator('#navbar .dropdown-menu.show');
    await expect(dropdownMenu).toHaveCSS('position', 'static');

    const toggleBox = await analyzeToggle.boundingBox();
    const menuBox = await dropdownMenu.boundingBox();
    expect(toggleBox).not.toBeNull();
    expect(menuBox).not.toBeNull();
    expect(menuBox!.y).toBeGreaterThan(toggleBox!.y);

    await page.locator(SELECTORS.NAV_WEEKLY_SUMMARY).click();
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/weekly_summary/);

    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);
    await openMobileNavbar(page);
    await openAnalyzeDropdown(page);
    await page.locator(SELECTORS.NAV_SESSION_SUMMARY).click();
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/session_summary/);
  });

  test('dark mode toggle still works after navbar restructure', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await page.evaluate(() => localStorage.setItem('darkMode', 'false'));
    await page.reload();
    await waitForPageReady(page);

    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await page.locator(SELECTORS.DARK_MODE_TOGGLE).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });
});
