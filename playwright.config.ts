import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const venvPython = process.platform === 'win32'
  ? path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
  : path.join(process.cwd(), '.venv', 'bin', 'python');
const pythonExecutable = fs.existsSync(venvPython) ? `"${venvPython}"` : 'python';
const reuseExistingServer = process.env.PW_REUSE_SERVER === '1' && !process.env.CI;
const configuredWorkers = Number(process.env.PW_WORKERS ?? '1');
const workers = Number.isFinite(configuredWorkers) && configuredWorkers > 0 ? configuredWorkers : 1;
const artifactsRoot = process.env.TEST_ARTIFACTS_DIR ?? 'artifacts';
const playwrightArtifactsDir = path.join(artifactsRoot, 'playwright');

/**
 * Playwright configuration for Hypertrophy Toolbox E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(playwrightArtifactsDir, 'report') }],
  ],
  outputDir: path.join(playwrightArtifactsDir, 'test-results'),
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://127.0.0.1:5000',
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    /* Video recording */
    video: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment to add more browsers
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: `${pythonExecutable} app.py`,
    url: 'http://127.0.0.1:5000',
    reuseExistingServer,
    timeout: 120 * 1000,
  },

  /* Global timeout settings */
  timeout: 30000,
  expect: {
    timeout: 10000,
  },
});
