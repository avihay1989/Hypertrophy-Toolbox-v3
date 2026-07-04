/**
 * E2E Test: Erase-data flow surfaces the auto-backup banner
 *
 * Track B WPB.8 (OD8) — /erase-data snapshots the live DB to
 * data/auto_backup/ before wiping it (utils/auto_backup.py::create_startup_backup).
 * The welcome page's confirm-erase handler must pass that snapshot's filename
 * to `showAutoBackupBanner()` so the user sees where the recoverable copy
 * landed. This spec fails without the wiring: the banner never appears.
 */
import { test, expect, ROUTES, waitForPageReady } from './fixtures';

const AUTO_BACKUP_BANNER = '[data-testid="auto-backup-banner"]';
const SNAPSHOT_FILENAME_PATTERN = /database_\d{8}_\d{6}\.db/;

test.describe('Erase flow — auto-backup banner', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.HOME);
    await waitForPageReady(page);
  });

  test('no banner is present before erase is confirmed', async ({ page }) => {
    await expect(page.locator(AUTO_BACKUP_BANNER)).toHaveCount(0);
  });

  test('confirming erase shows a banner referencing the data/auto_backup/ snapshot', async ({ page }) => {
    await page.locator('#eraseDataBtn').click();
    await expect(page.locator('#eraseDataModal')).toBeVisible();

    await page.locator('#confirmEraseBtn').click();

    const banner = page.locator(AUTO_BACKUP_BANNER);
    await expect(banner).toBeVisible();
    await expect(page.locator('#welcome > [data-testid="auto-backup-banner"]')).toHaveCount(1);
    await expect(banner).toContainText('Auto-backup created');
    await expect(banner).toContainText('data/auto_backup/');
    await expect(banner).toContainText(SNAPSHOT_FILENAME_PATTERN);
  });
});
