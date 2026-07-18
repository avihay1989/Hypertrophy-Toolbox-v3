/**
 * §4 visual-baseline sweep for free-exercise-db thumbnails.
 *
 * Validates rendering across the PLANNING §4.6 matrix:
 *   - /workout_plan and /workout_log
 *   - viewports: desktop (1440x900), tablet (768x1024), mobile (375x667)
 *   - themes: light, dark
 *   - view modes: simple, advanced (workout_plan only)
 *
 * Screenshots are locked via `toHaveScreenshot()` baselines under
 * e2e/__screenshots__/{platform}/visual-baseline-thumbnails.spec.ts-snapshots/.
 *
 * Requires the plan rows + media_path thumbnails from the committed visual
 * fixture. Run with the web server seeded by the visual seeder, i.e. set
 * PW_VISUAL_SEED=1 (see playwright.config.ts) so prepare_visual_db.py seeds the
 * throwaway DB before Flask opens it — the functional seed wipes user-state and
 * would leave this spec with no rows.
 */
import { test, expect, Page } from '@playwright/test';
import { ROUTES } from './fixtures';
import {
  elementScreenshotOptions,
  installDeterminism,
  prepareForScreenshot,
  type VisualTheme,
} from './visual-helpers';

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 },
] as const;

const THEMES: VisualTheme[] = ['light', 'dark'];
const PLAN_VIEW_MODES = ['simple', 'advanced'] as const;

// installDeterminism clears localStorage, so the plan view-mode flag must be set
// in an init script registered AFTER it (init scripts run in registration order).
async function applyPlanViewMode(page: Page, mode: 'simple' | 'advanced'): Promise<void> {
  await page.addInitScript((m) => {
    localStorage.setItem('hypertrophy_filter_view_mode', m);
  }, mode);
}

test.describe.configure({ mode: 'serial' });

test.describe('§4 visual baseline — workout_plan thumbnails', () => {
  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      for (const mode of PLAN_VIEW_MODES) {
        const label = `plan-${viewport.name}-${theme}-${mode}`;
        test(label, async ({ browser }) => {
          const context = await browser.newContext({
            viewport: { width: viewport.width, height: viewport.height },
          });
          const page = await context.newPage();
          await installDeterminism(page, { theme });
          await applyPlanViewMode(page, mode);

          await page.goto(ROUTES.WORKOUT_PLAN);
          await page.waitForSelector('#workout_plan_table_body tr', { timeout: 15_000 });

          // Behavioural assertions (deterministic across browsers).
          const rowCount = await page.locator('#workout_plan_table_body tr').count();
          expect(rowCount).toBeGreaterThanOrEqual(4);

          const thumbCount = await page.locator('#workout_plan_table_body img.exercise-thumbnail').count();
          expect(thumbCount).toBeGreaterThanOrEqual(1);

          for (const src of await page.locator('#workout_plan_table_body img.exercise-thumbnail').evaluateAll(
            (els) => els.map((el) => (el as HTMLImageElement).getAttribute('src') ?? ''),
          )) {
            expect(src).toMatch(/^\/static\/vendor\/free-exercise-db\/exercises\//);
            expect(src).not.toContain('..');
          }

          const htmlTheme = await page.locator('html').getAttribute('data-theme');
          expect(htmlTheme).toBe(theme);

          // Save screenshot artifact (full table only — keeps diff size sane).
          await prepareForScreenshot(page);
          const target = page.getByTestId('exercise-table');
          await expect(target).toHaveScreenshot(`${label}.png`, elementScreenshotOptions());

          await context.close();
        });
      }
    }
  }
});

test.describe('§4 visual baseline — workout_log thumbnails', () => {
  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      const label = `log-${viewport.name}-${theme}`;
      test(label, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
        });
        const page = await context.newPage();
        await installDeterminism(page, { theme });

        await page.goto(ROUTES.WORKOUT_LOG);
        await page.waitForLoadState('domcontentloaded');
        await page.waitForSelector('#workout-log-table tbody tr', { timeout: 15_000 });

        const rowCount = await page.locator('#workout-log-table tbody tr').count();
        expect(rowCount).toBeGreaterThanOrEqual(4);

        const thumbCount = await page.locator('#workout-log-table img.exercise-thumbnail').count();
        expect(thumbCount).toBeGreaterThanOrEqual(1);

        for (const src of await page.locator('#workout-log-table img.exercise-thumbnail').evaluateAll(
          (els) => els.map((el) => (el as HTMLImageElement).getAttribute('src') ?? ''),
        )) {
          expect(src).toMatch(/^\/static\/vendor\/free-exercise-db\/exercises\//);
          expect(src).not.toContain('..');
        }

        const htmlTheme = await page.locator('html').getAttribute('data-theme');
        expect(htmlTheme).toBe(theme);

        await prepareForScreenshot(page);
        const target = page.getByTestId('workout-log-table');
        await expect(target).toHaveScreenshot(`${label}.png`, elementScreenshotOptions());

        await context.close();
      });
    }
  }
});
