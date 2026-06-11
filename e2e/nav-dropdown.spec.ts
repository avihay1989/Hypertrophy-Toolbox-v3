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
  ROUTES.BODY_COMPOSITION,
  ROUTES.VOLUME_SPLITTER,
] as const;

async function openAnalyzeDropdown(page: Page, mode: 'hover' | 'click' = 'hover'): Promise<void> {
  const analyzeToggle = page.locator(ANALYZE_TOGGLE);
  await expect(analyzeToggle).toBeVisible();
  if (mode === 'hover') {
    await analyzeToggle.hover();
  } else {
    await analyzeToggle.click();
  }
  await expect(page.locator('#navbar .dropdown-menu.show')).toBeVisible();
}

async function openMobileNavbar(page: Page): Promise<void> {
  const collapse = page.locator('#navbarNav');
  const toggle = page.locator('#navbar .navbar-toggler');

  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(collapse).toHaveClass(/show/);
}

async function clickDarkModeToggle(page: Page): Promise<void> {
  await page.locator(SELECTORS.DARK_MODE_TOGGLE).click();
}

test.describe('P5 navbar dropdown and backup navigation', () => {
  test('top-level nav order matches the redesigned workflow', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    const labels = await page.locator('#navbarNav > ul.navbar-nav').first().evaluate((navList) =>
      Array.from(navList.children).map((item) => {
        const link = item.querySelector(':scope > .nav-link');
        return (link?.textContent || '').trim().replace(/\s+/g, ' ');
      })
    );

    expect(labels).toEqual([
      'Plan',
      'Log',
      'Analyze',
      'Progress',
      'Profile',
      'Body Composition',
      'Distribute',
      'Backup',
    ]);

    const overflowingLabels = await page.locator('#navbarNav > ul.navbar-nav').first().evaluate((navList) =>
      Array.from(navList.querySelectorAll(':scope > .nav-item > .nav-link'))
        .filter((link) => link.scrollWidth > link.clientWidth + 1)
        .map((link) => (link.textContent || '').trim().replace(/\s+/g, ' '))
    );
    expect(overflowingLabels).toEqual([]);
  });

  test('Analyze dropdown opens on hover and contains Weekly and Session links', async ({ page }) => {
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

  test('static Font Awesome nav icons have accent color and hover motion', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    const profileIcon = page.locator('#nav-user-profile .nav-fa-icon');
    const bodyCompositionIcon = page.locator('#nav-body-composition .nav-fa-icon');
    const backupIcon = page.locator('#nav-backup .nav-fa-icon');

    await expect(profileIcon).toHaveCSS('color', 'rgb(109, 93, 252)');
    await expect(bodyCompositionIcon).toHaveCSS('color', 'rgb(15, 159, 143)');
    await expect(backupIcon).toHaveCSS('color', 'rgb(217, 119, 6)');

    await page.locator('#nav-user-profile').hover();
    await expect(profileIcon).toHaveCSS('transform', 'none');

    await page.locator('#nav-backup').hover();
    await expect(backupIcon).not.toHaveCSS('transform', 'none');
  });

  test('Backup nav points to the dedicated backup page', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    const backup = page.locator(SELECTORS.NAV_BACKUP);
    await expect(backup).toBeVisible();
    await expect(backup).toHaveAttribute('href', '/backup');
  });

  test('Backup nav opens the dedicated backup page from every page', async ({ page }) => {
    for (const route of ROUTE_LIST) {
      await page.goto(route);
      await waitForPageReady(page);

      await page.locator(SELECTORS.NAV_BACKUP).click();
      await waitForPageReady(page);
      await expect(page).toHaveURL(/\/backup/);
      await expect(page.locator(SELECTORS.PAGE_BACKUP)).toBeVisible();
    }
  });

  test('mobile Analyze dropdown expands inline and links navigate', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await openMobileNavbar(page);
    await openAnalyzeDropdown(page, 'click');

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
    await openAnalyzeDropdown(page, 'click');
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
    await expect(page.locator(SELECTORS.DARK_MODE_TOGGLE)).toBeVisible();
    await clickDarkModeToggle(page);
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });
});
