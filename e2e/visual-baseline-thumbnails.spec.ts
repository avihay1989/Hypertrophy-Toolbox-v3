/**
 * §4 visual-baseline sweep for free-exercise-db thumbnails.
 *
 * Validates rendering across the PLANNING §4.6 matrix:
 *   - /workout_plan and /workout_log
 *   - viewports: desktop (1440x900), tablet (768x1024), mobile (375x667)
 *   - themes: light, dark
 *   - view modes: simple, advanced (workout_plan only)
 *
 * Screenshots saved under e2e/artifacts/visual-baseline/ for inspection;
 * NOT committed as `toHaveScreenshot()` baselines yet -- first-run
 * baseline commit is owner-eyes-on.
 *
 * Requires the worktree DB to be seeded by
 *   scripts/seed_visual_baseline.py
 * and the apply step (`scripts/apply_free_exercise_db_mapping.py`) to
 * have populated media_path values.
 */
import { test, expect, Page } from '@playwright/test';
import { ROUTES } from './fixtures';
import { promises as fs } from 'fs';
import * as path from 'path';

const ARTIFACT_DIR = path.join(__dirname, 'artifacts', 'visual-baseline');

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 },
] as const;

const THEMES = ['light', 'dark'] as const;
const PLAN_VIEW_MODES = ['simple', 'advanced'] as const;

async function applyTheme(page: Page, theme: 'light' | 'dark'): Promise<void> {
  await page.addInitScript((t) => {
    localStorage.setItem('darkMode', t === 'dark' ? 'true' : 'false');
  }, theme);
}

async function applyPlanViewMode(page: Page, mode: 'simple' | 'advanced'): Promise<void> {
  await page.addInitScript((m) => {
    localStorage.setItem('hypertrophy_filter_view_mode', m);
  }, mode);
}

async function ensureArtifactDir(): Promise<void> {
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
}

test.describe.configure({ mode: 'serial' });

test.describe('§4 visual baseline — workout_plan thumbnails', () => {
  test.beforeAll(async () => {
    await ensureArtifactDir();
  });

  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      for (const mode of PLAN_VIEW_MODES) {
        const label = `plan-${viewport.name}-${theme}-${mode}`;
        test(label, async ({ browser }) => {
          const context = await browser.newContext({
            viewport: { width: viewport.width, height: viewport.height },
          });
          const page = await context.newPage();
          await applyTheme(page, theme);
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
          const target = page.locator('.workout-plan-table, #workout_plan_table_body').first();
          await target.screenshot({ path: path.join(ARTIFACT_DIR, `${label}.png`) });

          await context.close();
        });
      }
    }
  }
});

test.describe('§4 visual baseline — workout_log thumbnails', () => {
  test.beforeAll(async () => {
    await ensureArtifactDir();
  });

  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      const label = `log-${viewport.name}-${theme}`;
      test(label, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
        });
        const page = await context.newPage();
        await applyTheme(page, theme);

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

        const target = page.locator('.workout-log-table, #workout-log-table').first();
        await target.screenshot({ path: path.join(ARTIFACT_DIR, `${label}.png`) });

        await context.close();
      });
    }
  }
});
