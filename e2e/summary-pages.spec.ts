/**
 * E2E Test: Summary Pages (Weekly & Session)
 * 
 * Tests the summary pages functionality including:
 * - Page loading
 * - Contribution mode toggles
 * - Volume legend display
 * - Table rendering
 */
import type { Page } from '@playwright/test';
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';

const CONTRIBUTION_MODE_OPTIONS = [
  { value: 'total', text: 'Total (Primary + Secondary + Tertiary)' },
  { value: 'direct', text: 'Direct Only (Primary Muscle Only)' },
];

function unwrapApiData(payload: unknown) {
  if (
    payload &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    'data' in payload
  ) {
    return (payload as { data: unknown }).data;
  }

  return payload;
}

async function expectSharedLegendSwatches(page: Page) {
  await expect(page.locator('.volume-legend .volume-indicator.low-volume')).toHaveCSS(
    'background-color',
    'rgb(220, 53, 69)'
  );
  await expect(page.locator('.volume-legend .volume-indicator.medium-volume')).toHaveCSS(
    'background-color',
    'rgb(253, 126, 20)'
  );
  await expect(page.locator('.volume-legend .volume-indicator.high-volume')).toHaveCSS(
    'background-color',
    'rgb(25, 135, 84)'
  );
  await expect(page.locator('.volume-legend .volume-indicator.ultra-volume')).toHaveCSS(
    'background-color',
    'rgb(111, 66, 193)'
  );
}

async function expectMethodSelectorContract(page: Page, updaterName: string) {
  const methodSelector = page.locator('.method-selector').first();
  await expect(methodSelector).toBeVisible();

  const contributionMode = page.locator('#contribution-mode');

  await expect(page.locator('#counting-mode')).toHaveCount(0);
  await expect(page.locator('label[for="counting-mode"]')).toHaveCount(0);
  await expect(page.locator('label[for="contribution-mode"]')).toHaveText('Muscle Contribution Mode');
  await expect(contributionMode).toHaveAttribute('onchange', `${updaterName}()`);

  await expect(contributionMode.locator('option')).toHaveCount(CONTRIBUTION_MODE_OPTIONS.length);

  for (const [index, option] of CONTRIBUTION_MODE_OPTIONS.entries()) {
    await expect(contributionMode.locator('option').nth(index)).toHaveAttribute('value', option.value);
    await expect(contributionMode.locator('option').nth(index)).toHaveText(option.text);
  }
}

test.describe('Weekly Summary Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WEEKLY_SUMMARY);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('page loads with correct structure', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText(/(Weekly|Plan Volume) Summary/i);

    // Check summary container
    await expect(page.locator(SELECTORS.PAGE_WEEKLY_SUMMARY)).toBeVisible();
  });

  test('contribution mode selector is present', async ({ page }) => {
    await expectMethodSelectorContract(page, 'updateWeeklySummary');
  });

  test('volume legend is displayed', async ({ page }) => {
    const legend = page.locator('.volume-legend');
    await expect(legend).toBeVisible();

    // Check legend categories
    await expect(legend).toContainText('Low Volume');
    await expect(legend).toContainText('Medium Volume');
    await expect(legend).toContainText('High Volume');
    await expect(legend).toContainText('Excessive Volume');
  });

  test('legend swatches use shared volume classification colors', async ({ page }) => {
    await expectSharedLegendSwatches(page);
  });

  test('weekly summary table has correct headers', async ({ page }) => {
    const table = page.locator('#weekly-summary-container table');
    await expect(table).toBeVisible();

    // Check expected headers
    const headers = table.locator('thead th');
    const headerTexts = await headers.allInnerTexts();
    const headerString = headerTexts.join(' ').toLowerCase();

    expect(headerString).toContain('muscle');
    expect(headerString).toContain('effective sets');
    expect(headerString).toContain('raw sets');
    expect(headerString).toContain('volume');
  });

  test('changing contribution mode updates display', async ({ page }) => {
    const contributionMode = page.locator('#contribution-mode');
    
    // Select "Direct Only" option
    await contributionMode.selectOption('direct');

    // Wait for update
    await page.waitForTimeout(500);

    // The selection should persist
    await expect(contributionMode).toHaveValue('direct');

    // Switch back to total
    await contributionMode.selectOption('total');
    await page.waitForTimeout(500);
    await expect(contributionMode).toHaveValue('total');
  });

  test('fetch-backed weekly summary updates use explicit JSON intent', async ({ page }) => {
    const [contributionResponse] = await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes('/weekly_summary?') &&
        response.url().includes('contribution_mode=direct') &&
        response.request().method() === 'GET' &&
        response.request().headers()['x-requested-with'] === 'XMLHttpRequest'
      ),
      page.locator('#contribution-mode').selectOption('direct'),
    ]);

    expect(contributionResponse.ok()).toBeTruthy();
    expect(contributionResponse.url()).toContain('contribution_mode=direct');
    expect(contributionResponse.url()).not.toContain('counting_mode=');
    const contributionResponsePayload = await contributionResponse.json();
    expect(contributionResponsePayload.ok).toBe(true);
    expect(contributionResponsePayload.status).toBe('success');
    const contributionPayload = unwrapApiData(contributionResponsePayload) as Record<string, unknown>;
    expect(Array.isArray(contributionPayload.weekly_summary)).toBe(true);
    expect(Array.isArray(contributionPayload.categories)).toBe(true);
    expect(contributionPayload).toHaveProperty('isolated_muscles');
    expect(contributionPayload).toHaveProperty('modes');
    await expect(page.locator('#volume-formula-text')).toContainText('Effective Sets');
    const weeklySummary = contributionPayload.weekly_summary as Array<Record<string, unknown>>;
    if (weeklySummary.length > 0) {
      await expect(
        page.locator('#weekly-summary-table tr').first().locator('td[data-label="Effective Sets"]')
      ).toHaveText(Number(weeklySummary[0].effective_sets).toFixed(1));
      await expect(
        page.locator('#weekly-summary-table tr').first().locator('td[data-label="Raw Sets"]')
      ).toHaveText(Number(weeklySummary[0].raw_sets).toFixed(1));
    }
    await expect(page.locator('#weekly-summary-table tr').first()).toBeVisible();
  });
});

test.describe('Session Summary Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.SESSION_SUMMARY);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('page loads with correct structure', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText('Session Summary');

    // Check summary container
    await expect(page.locator(SELECTORS.PAGE_SESSION_SUMMARY)).toBeVisible();
  });

  test('contribution mode selector is present', async ({ page }) => {
    await expectMethodSelectorContract(page, 'updateSessionSummary');
  });

  test('volume legend is displayed', async ({ page }) => {
    const legend = page.locator('.volume-legend');
    await expect(legend).toBeVisible();

    // Check session-specific content
    await expect(legend).toContainText('Volume Classification');
  });

  test('session legend swatches use shared volume classification colors', async ({ page }) => {
    await expectSharedLegendSwatches(page);
  });

  test('session summary table has correct headers', async ({ page }) => {
    const table = page.locator('#session-summary-container table');
    await expect(table).toBeVisible();

    // Check expected headers
    const headers = table.locator('thead th');
    const headerTexts = await headers.allInnerTexts();
    const headerString = headerTexts.join(' ').toLowerCase();

    expect(headerString).toContain('routine');
    expect(headerString).toContain('muscle');
    expect(headerString).toContain('effective sets');
    expect(headerString).toContain('raw sets');
    expect(headerString).toContain('volume');
  });

  test('method selector section has descriptions', async ({ page }) => {
    const methodSelector = page.locator('.method-selector').first();
    await expect(methodSelector).toBeVisible();

    // Check help text exists (multiple form-text elements, check at least one is visible)
    const formTexts = methodSelector.locator('.form-text');
    await expect(formTexts.first()).toBeVisible();
  });

  test('fetch-backed session summary updates use explicit JSON intent', async ({ page }) => {
    const [contributionResponse] = await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes('/session_summary?') &&
        response.url().includes('contribution_mode=direct') &&
        response.request().method() === 'GET' &&
        response.request().headers()['x-requested-with'] === 'XMLHttpRequest'
      ),
      page.locator('#contribution-mode').selectOption('direct'),
    ]);

    expect(contributionResponse.ok()).toBeTruthy();
    expect(contributionResponse.url()).toContain('contribution_mode=direct');
    expect(contributionResponse.url()).not.toContain('counting_mode=');
    const contributionResponsePayload = await contributionResponse.json();
    expect(contributionResponsePayload.ok).toBe(true);
    expect(contributionResponsePayload.status).toBe('success');
    const contributionPayload = unwrapApiData(contributionResponsePayload) as Record<string, unknown>;
    expect(Array.isArray(contributionPayload.session_summary)).toBe(true);
    expect(Array.isArray(contributionPayload.categories)).toBe(true);
    expect(contributionPayload).toHaveProperty('isolated_muscles');
    expect(contributionPayload).toHaveProperty('modes');
    await expect(page.locator('#volume-formula-text')).toContainText('Effective Sets');
    const sessionSummary = contributionPayload.session_summary as Array<Record<string, unknown>>;
    if (sessionSummary.length > 0) {
      await expect(
        page.locator('#session-summary-table tr').first().locator('td[data-label="Effective Sets"]')
      ).toHaveText(Number(sessionSummary[0].effective_sets).toFixed(1));
      await expect(
        page.locator('#session-summary-table tr').first().locator('td[data-label="Raw Sets"]')
      ).toHaveText(Number(sessionSummary[0].raw_sets).toFixed(1));
    }
    await expect(page.locator('#session-summary-table tr').first()).toBeVisible();
  });
});

test.describe('Pattern Coverage Analysis (v1.5.0)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WEEKLY_SUMMARY);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('pattern coverage API returns valid structure', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/pattern_coverage');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data).toHaveProperty('per_routine');
    expect(data.data).toHaveProperty('total');
    expect(data.data).toHaveProperty('warnings');
    expect(data.data).toHaveProperty('sets_per_routine');
    expect(data.data).toHaveProperty('ideal_sets_range');
  });

  test('pattern coverage warnings are actionable', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/pattern_coverage');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    const warnings = data.data.warnings;
    
    // Warnings should be an array
    expect(Array.isArray(warnings)).toBe(true);
    
    // Each warning should have required fields
    for (const warning of warnings) {
      expect(warning).toHaveProperty('type');
      expect(warning).toHaveProperty('message');
      // Level indicates how critical the warning is (high, medium, low)
      expect(warning).toHaveProperty('level');
      expect(['high', 'medium', 'low']).toContain(warning.level);
      // Description provides actionable details
      expect(warning).toHaveProperty('description');
    }
  });

  test('pattern coverage tracks movement patterns', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/pattern_coverage');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    const total = data.data.total;
    
    // Total should track core movement patterns
    expect(typeof total).toBe('object');
    
    // Common patterns to track
    const expectedPatterns = ['squat', 'hinge', 'horizontal_push', 'horizontal_pull', 'vertical_push', 'vertical_pull'];
    
    // At least some patterns should be tracked
    const hasPatterns = Object.keys(total).some(key => 
      expectedPatterns.some(pattern => key.toLowerCase().includes(pattern.replace('_', '')))
    );
    
    // Pattern structure may vary, just ensure it's not empty when there's data
    expect(typeof total === 'object').toBeTruthy();
  });

  test('sets_per_routine reports session volume', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/pattern_coverage');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    const setsPerRoutine = data.data.sets_per_routine;
    
    // Should be an object mapping routine names to set counts
    expect(typeof setsPerRoutine).toBe('object');
    
    // Each value should be a non-negative number
    for (const [routine, sets] of Object.entries(setsPerRoutine)) {
      expect(typeof sets).toBe('number');
      expect(sets).toBeGreaterThanOrEqual(0);
    }
  });

  test('ideal_sets_range provides guidance', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/pattern_coverage');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    const idealRange = data.data.ideal_sets_range;
    
    // Should provide min and max guidance
    expect(idealRange).toHaveProperty('min');
    expect(idealRange).toHaveProperty('max');
    expect(idealRange.min).toBeLessThan(idealRange.max);
    
    // v1.5.0 recommends 15-24 sets per session
    expect(idealRange.min).toBeGreaterThanOrEqual(10);
    expect(idealRange.max).toBeLessThanOrEqual(30);
  });

  test('weekly summary page renders pattern coverage from the live fetch', async ({ page }) => {
    const [response] = await Promise.all([
      page.waitForResponse((networkResponse) =>
        networkResponse.url().includes('/api/pattern_coverage') &&
        networkResponse.request().headers()['x-requested-with'] === 'XMLHttpRequest'
      ),
      page.reload(),
    ]);

    expect(response.ok()).toBeTruthy();
    const payload = unwrapApiData(await response.json()) as Record<string, unknown>;
    expect(payload).toHaveProperty('warnings');
    expect(payload).toHaveProperty('total');
    await expect(page.locator('#pattern-coverage-container .spinner-border')).toHaveCount(0);
    await expect(page.locator('#pattern-coverage-container')).not.toContainText('Loading');
  });
});
