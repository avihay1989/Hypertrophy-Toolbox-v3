/**
 * Strict fixtures for redesign gates.
 *
 * The legacy fixture intentionally ignores broad null/undefined JavaScript
 * errors for older E2E coverage. Redesign specs should fail on those errors so
 * broken selectors cannot hide behind screenshot diffs.
 */
import { test as base, expect } from '@playwright/test';

import {
  API_ENDPOINTS,
  ROUTES,
  SELECTORS,
  expectToast,
  getDarkModeState,
  getStoredDarkMode,
  resetWorkoutPlan,
  waitForPageReady,
} from './fixtures';

function isNonCriticalConsoleError(text: string): boolean {
  return (
    text.includes('favicon') ||
    text.includes('Source map') ||
    text.includes('[HMR]')
  );
}

export const test = base.extend({
  page: async ({ page }, use) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;

      const text = msg.text();
      if (!isNonCriticalConsoleError(text)) {
        errors.push(`Console Error: ${text}`);
      }
    });

    page.on('pageerror', (error) => {
      errors.push(`Page Error: ${error.stack || error.message}`);
    });

    await use(page);

    expect(errors, 'unexpected browser errors').toEqual([]);
  },
});

export {
  API_ENDPOINTS,
  ROUTES,
  SELECTORS,
  expect,
  expectToast,
  getDarkModeState,
  getStoredDarkMode,
  resetWorkoutPlan,
  waitForPageReady,
};
