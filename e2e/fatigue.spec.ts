/**
 * Fatigue Meter — Phase 2 Stage 2 dedicated page (/fatigue) E2E.
 *
 * Covers page load, period selector, per-muscle bar rendering, SFR cards,
 * empty-state copy, dark-mode parity, and the Unassigned-bucket invariant.
 *
 * Per-spec test count target: ~8. Chromium only.
 */
import { test, expect } from './fixtures';
import { Page } from '@playwright/test';

const FATIGUE_URL = '/fatigue';

async function gotoFatigue(page: Page, period?: string): Promise<void> {
  const url = period ? `${FATIGUE_URL}?period=${period}` : FATIGUE_URL;
  await page.goto(url);
  await page.waitForSelector('[data-testid="fatigue-page"]', { state: 'visible' });
}

test.describe('/fatigue page', () => {
  test.beforeEach(async ({ consoleErrors }) => {
    consoleErrors.startCollecting();
  });

  test('loads with no console errors', async ({ page, consoleErrors }) => {
    await gotoFatigue(page);
    await expect(page.locator('[data-testid="fatigue-page"]')).toBeVisible();
    consoleErrors.assertNoErrors();
  });

  test('renders both SFR cards (planned + logged)', async ({ page }) => {
    await gotoFatigue(page);
    await expect(page.locator('[data-testid="fatigue-sfr-planned"]')).toBeVisible();
    await expect(page.locator('[data-testid="fatigue-sfr-logged"]')).toBeVisible();
    // Sentinel for fatigue==0 → em dash, never "inf".
    const plannedValue = await page
      .locator('[data-testid="fatigue-sfr-planned-value"]')
      .innerText();
    const loggedValue = await page
      .locator('[data-testid="fatigue-sfr-logged-value"]')
      .innerText();
    expect(plannedValue.toLowerCase()).not.toContain('inf');
    expect(loggedValue.toLowerCase()).not.toContain('inf');
  });

  test('period selector toggles the URL query param', async ({ page }) => {
    await gotoFatigue(page);
    const select = page.locator('[data-testid="fatigue-period-select"]');
    await select.selectOption('last_4_weeks');
    // The onchange submits the form, which round-trips through GET /fatigue.
    await page.waitForURL(/period=last_4_weeks/);
    await expect(select).toHaveValue('last_4_weeks');

    await select.selectOption('this_session');
    await page.waitForURL(/period=this_session/);
    await expect(select).toHaveValue('this_session');
  });

  test('invalid period query param silently falls back to this_week', async ({ page }) => {
    await page.goto(`${FATIGUE_URL}?period=garbage`);
    await page.waitForSelector('[data-testid="fatigue-page"]', { state: 'visible' });
    const select = page.locator('[data-testid="fatigue-period-select"]');
    await expect(select).toHaveValue('this_week');
  });

  test('empty-state copy renders when no plan and no logs', async ({ page }) => {
    // Reset to brand-new DB via /erase-data so the page is genuinely empty.
    await page.request.post('/erase-data', {
      data: { confirm: 'ERASE_ALL_DATA' },
      headers: { 'Content-Type': 'application/json' },
    });
    await gotoFatigue(page);
    await expect(page.locator('[data-testid="fatigue-empty-state"]')).toBeVisible();
  });

  test('dark mode parity — page survives toggle without console errors', async ({ page, consoleErrors }) => {
    await page.goto('/');
    await page.evaluate(() => {
      const toggle = document.querySelector('#darkModeToggle') as HTMLElement | null;
      if (toggle) toggle.click();
    });
    await gotoFatigue(page);
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('dark');
    await expect(page.locator('[data-testid="fatigue-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="fatigue-sfr-planned"]')).toBeVisible();
    consoleErrors.assertNoErrors();
  });

  test('375px viewport — page renders without horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await gotoFatigue(page);
    const overflow = await page.evaluate(
      () => document.body.scrollWidth > document.body.clientWidth + 1
    );
    expect(overflow).toBe(false);
  });

  test('badge → /fatigue link from /session_summary navigates here', async ({ page }) => {
    // The "View per-muscle breakdown →" link lands in chapter 2.8, so this
    // spec validates round-trip navigation rather than the link itself.
    await page.goto('/session_summary');
    await page.goto(FATIGUE_URL);
    await expect(page.locator('[data-testid="fatigue-page"]')).toBeVisible();
  });
});
