/**
 * E2E Test: Smoke and Navigation
 * 
 * Tests that the app loads correctly and navigation works
 * as expected across all main routes.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';

test.describe('Global Smoke and Navigation', () => {
  test.beforeEach(async ({ consoleErrors }) => {
    consoleErrors.startCollecting();
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('home page loads with navbar and key links visible', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    // Assert navbar exists
    const navbar = page.locator(SELECTORS.NAVBAR);
    await expect(navbar).toBeVisible();

    // Assert brand link
    const brand = page.locator(SELECTORS.NAV_BRAND);
    await expect(brand).toBeVisible();
    await expect(brand).toContainText('Hypertrophy Toolbox');

    // Assert all nav links are visible
    await expect(page.locator(SELECTORS.NAV_WORKOUT_PLAN)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_WEEKLY_SUMMARY)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_SESSION_SUMMARY)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_WORKOUT_LOG)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_PROGRESSION_PLAN)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_VOLUME_SPLITTER)).toBeVisible();

    // Assert dark mode toggle is visible
    await expect(page.locator(SELECTORS.DARK_MODE_TOGGLE)).toBeVisible();
  });

  test('home page displays welcome content', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    // Assert welcome page is loaded
    const welcomePage = page.locator(SELECTORS.PAGE_WELCOME);
    await expect(welcomePage).toBeVisible();

    // Check for hero heading
    await expect(page.locator('h1')).toContainText('Hypertrophy');
  });

  test('navigate to Workout Plan via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    // Click workout plan nav link
    await page.locator(SELECTORS.NAV_WORKOUT_PLAN).click();
    await waitForPageReady(page);

    // Verify we're on workout plan page
    await expect(page).toHaveURL(/\/workout_plan/);
    const workoutPage = page.locator(SELECTORS.PAGE_WORKOUT_PLAN);
    await expect(workoutPage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Workout Plan');
  });

  test('navigate to Weekly Summary via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await page.locator(SELECTORS.NAV_WEEKLY_SUMMARY).click();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/\/weekly_summary/);
    const summaryPage = page.locator(SELECTORS.PAGE_WEEKLY_SUMMARY);
    await expect(summaryPage).toBeVisible();
    await expect(page.locator('h1')).toContainText(/(Weekly|Plan Volume) Summary/i);
  });

  test('navigate to Session Summary via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await page.locator(SELECTORS.NAV_SESSION_SUMMARY).click();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/\/session_summary/);
    const sessionPage = page.locator(SELECTORS.PAGE_SESSION_SUMMARY);
    await expect(sessionPage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Session Summary');
  });

  test('navigate to Workout Log via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await page.locator(SELECTORS.NAV_WORKOUT_LOG).click();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/\/workout_log/);
    const logPage = page.locator(SELECTORS.PAGE_WORKOUT_LOG);
    await expect(logPage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Workout Log');
  });

  test('navigate to Progression Plan via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await page.locator(SELECTORS.NAV_PROGRESSION_PLAN).click();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/\/progression/);
    const progressionPage = page.locator(SELECTORS.PAGE_PROGRESSION);
    await expect(progressionPage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Progression Plan');
  });

  test('navigate to Volume Splitter via navbar', async ({ page }) => {
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);

    await page.locator(SELECTORS.NAV_VOLUME_SPLITTER).click();
    await waitForPageReady(page);

    await expect(page).toHaveURL(/\/volume_splitter/);
    const volumePage = page.locator(SELECTORS.PAGE_VOLUME_SPLITTER);
    await expect(volumePage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Volume Splitter');
  });

  test('navigate back to home via brand link', async ({ page }) => {
    // Start from workout plan page
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    // Click brand to go home
    await page.locator(SELECTORS.NAV_BRAND).click();
    await waitForPageReady(page);

    // Verify we're on home page
    await expect(page).toHaveURL(/\/$/);
    const welcomePage = page.locator(SELECTORS.PAGE_WELCOME);
    await expect(welcomePage).toBeVisible();
  });

  test('all pages accessible without errors (full navigation cycle)', async ({ page }) => {
    const routes = [
      { url: ROUTES.HOME, selector: SELECTORS.PAGE_WELCOME },
      { url: ROUTES.WORKOUT_PLAN, selector: SELECTORS.PAGE_WORKOUT_PLAN },
      { url: ROUTES.WEEKLY_SUMMARY, selector: SELECTORS.PAGE_WEEKLY_SUMMARY },
      { url: ROUTES.SESSION_SUMMARY, selector: SELECTORS.PAGE_SESSION_SUMMARY },
      { url: ROUTES.WORKOUT_LOG, selector: SELECTORS.PAGE_WORKOUT_LOG },
      { url: ROUTES.PROGRESSION, selector: SELECTORS.PAGE_PROGRESSION },
      { url: ROUTES.VOLUME_SPLITTER, selector: SELECTORS.PAGE_VOLUME_SPLITTER },
    ];

    for (const route of routes) {
      await page.goto(route.url);
      await waitForPageReady(page);
      await expect(page.locator(route.selector)).toBeVisible({ timeout: 10000 });
    }
  });
});
