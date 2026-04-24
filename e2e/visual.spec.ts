import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

import { test, expect, ROUTES, waitForPageReady } from './strict-fixtures';
import {
  installDeterminism,
  prepareForScreenshot,
  visualScreenshotOptions,
  type VisualTheme,
} from './visual-helpers';

const pages = [
  { name: 'welcome', route: ROUTES.HOME },
  { name: 'workout-plan', route: ROUTES.WORKOUT_PLAN },
  { name: 'workout-log', route: ROUTES.WORKOUT_LOG },
  { name: 'weekly-summary', route: ROUTES.WEEKLY_SUMMARY },
  { name: 'session-summary', route: ROUTES.SESSION_SUMMARY },
  { name: 'progression', route: ROUTES.PROGRESSION },
  { name: 'volume-splitter', route: ROUTES.VOLUME_SPLITTER },
] as const;

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
] as const;

const themes: VisualTheme[] = ['light', 'dark'];

test.beforeAll(() => {
  const venvPython = process.platform === 'win32'
    ? path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
    : path.join(process.cwd(), '.venv', 'bin', 'python');
  const pythonExecutable = fs.existsSync(venvPython) ? venvPython : 'python';
  const databasePath = process.env.DB_FILE ?? path.join(process.cwd(), 'data', 'database.db');
  execFileSync(pythonExecutable, [
    'e2e/scripts/prepare_visual_db.py',
    '--output',
    databasePath,
  ], { stdio: 'ignore' });
});

for (const appPage of pages) {
  test.describe(`visual baseline: ${appPage.name}`, () => {
    for (const viewport of viewports) {
      for (const theme of themes) {
        test(`${appPage.name} ${viewport.name} ${theme}`, async ({ page }) => {
          await page.setViewportSize({
            width: viewport.width,
            height: viewport.height,
          });

          await installDeterminism(page, { theme });
          await page.goto(appPage.route);
          await waitForPageReady(page);
          await prepareForScreenshot(page);

          await expect(page).toHaveScreenshot(
            `${appPage.name}-${viewport.name}-${theme}.png`,
            visualScreenshotOptions(page),
          );
        });
      }
    }
  });
}
