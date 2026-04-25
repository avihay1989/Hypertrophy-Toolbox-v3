/**
 * E2E Test: Backup Center
 *
 * Covers the dedicated backup page plus its entry points from Workout Plan.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, expectToast } from './fixtures';

test.describe('Backup Center Entry Points', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('backup center link is visible next to clear plan and targets the browse intent', async ({ page }) => {
    const programActions = page.getByRole('group', { name: 'Program actions' });
    const libraryBtn = page.locator('#load-program-btn');
    const actionIds = await programActions.locator('.inline-control-item > :is(a, button)').evaluateAll((elements) =>
      elements.map((element) => element.id),
    );

    await expect(programActions.locator('#save-program-btn')).toHaveCount(0);
    expect(actionIds).toEqual(['load-program-btn', 'clear-plan-btn']);
    await expect(libraryBtn).toBeVisible();
    await expect(libraryBtn).toContainText('Backup Center');
    await expect(libraryBtn).toHaveAttribute('href', '/backup?intent=browse');
  });

  test('backup center link lands on the browse pane', async ({ page }) => {
    await page.locator('#load-program-btn').click();
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/backup\?intent=browse/);
    await expect(page.locator('#backup-search')).toBeFocused();
    await expect(page.locator('#backup-library-panel')).toHaveClass(/is-targeted/);
  });
});

test.describe('Backup Center Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.request.post('/clear_workout_plan', { failOnStatusCode: false });
    const seedResponse = await page.request.post('/add_exercise', {
      data: {
        routine: 'GYM - Full Body - Workout A',
        exercise: 'Bench Press',
        sets: 3,
        min_rep_range: 6,
        max_rep_range: 8,
        weight: 100,
      },
    });
    expect(seedResponse.ok()).toBeTruthy();
    await page.goto(ROUTES.BACKUP);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('dedicated backup center page renders', async ({ page }) => {
    await expect(page.locator(SELECTORS.PAGE_BACKUP)).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Backup Center' })).toBeVisible();
    await expect(page.locator('#backup-center-save-form')).toBeVisible();
    await expect(page.locator('#backup-center-list')).toBeVisible();
  });

  test('backup center requires a backup name', async ({ page }) => {
    await page.locator('#backup-center-name').fill('');
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, 'Please enter a name for the backup.');
    await expect(page.locator('#backup-center-name')).toBeFocused();
  });

  test('can create a backup from the dedicated page', async ({ page }) => {
    const backupName = `Backup Center E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-note').fill('Created from the dedicated backup center.');
    await page.locator('#backup-center-save-submit').click();

    await expectToast(page, backupName);
    await page.locator('#backup-search').fill(backupName);
    await expect(page.locator('#backup-center-list')).toContainText(backupName);
  });

  test('restore and delete actions use inline confirmation on the detail pane', async ({ page }) => {
    const backupName = `Backup Action E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);

    const record = page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first();
    await expect(record).toBeVisible();
    await record.click();

    await expect(page.locator('#backup-detail-name')).toContainText(backupName);

    await page.locator('#backup-detail-restore').click();
    await expect(page.locator('#backup-action-confirm')).toBeVisible();
    await expect(page.locator('#backup-action-title')).toContainText('Confirm restore');
    await expect(page.locator('#confirmRestoreModal')).toHaveCount(0);

    await page.locator('#backup-action-cancel').click();
    await expect(page.locator('#backup-action-confirm')).not.toBeVisible();

    await page.locator('#backup-detail-delete').click();
    await expect(page.locator('#backup-action-confirm')).toBeVisible();
    await expect(page.locator('#backup-action-title')).toContainText('Confirm delete');
    await expect(page.locator('#confirmDeleteModal')).toHaveCount(0);
  });

  test('restore confirmation mentions logged sessions and offers a save-first snapshot', async ({ page }) => {
    const backupName = `Restore Copy E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await page.locator('#backup-detail-restore').click();

    await expect(page.locator('#backup-action-text')).toContainText('logged sessions will be cleared');
    await expect(page.locator('#backup-restore-save-first')).toBeVisible();

    await page.locator('#backup-action-cancel').click();
    await expect(page.locator('#backup-action-confirm')).not.toBeVisible();
  });

  test('save-first snapshot creates a pre-restore backup before restore', async ({ page }) => {
    const backupName = `Save First E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await page.locator('#backup-detail-restore').click();
    await page.locator('#backup-restore-save-first').click();

    await expectToast(page, 'Current plan saved as');
    await page.locator('#backup-search').fill('Pre-restore snapshot');
    await expect(page.locator('#backup-center-list')).toContainText('Pre-restore snapshot');
    await expect(page.locator('#backup-action-confirm')).not.toBeVisible();
  });

  test('restore renders a warning inline result panel when nothing can be restored', async ({ page }) => {
    const backupName = `Restore Result E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await page.locator('#backup-detail-restore').click();
    await page.route('**/api/backups/*/restore', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            backup_id: 1,
            backup_name: backupName,
            restored_count: 0,
            skipped: ['Missing from catalog'],
          },
        }),
      });
    });
    await page.locator('#backup-action-confirm-btn').click();

    await expect(page.locator('#backup-restore-result')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#backup-restore-result')).toHaveClass(/is-warning/);
    await expect(page.locator('#backup-restore-result-title')).toContainText('Nothing was restored');
    await expect(page.locator('#backup-restore-result-list li')).toHaveCount(1);
  });

  test('restore with missing exercises shows skipped names inline', async ({ page }) => {
    const backupName = `Partial Restore E2E ${Date.now()}`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await page.locator('#backup-detail-restore').click();
    await page.route('**/api/backups/*/restore', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            backup_id: 1,
            backup_name: backupName,
            restored_count: 3,
            skipped: ['Missing Exercise A', 'Missing Exercise B'],
          },
        }),
      });
    });
    await page.locator('#backup-action-confirm-btn').click();

    await expect(page.locator('#backup-restore-result')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#backup-restore-result')).not.toHaveClass(/is-warning/);
    await expect(page.locator('#backup-restore-result-title')).toContainText('3 exercises restored');
    await expect(page.locator('#backup-restore-result-title')).toContainText('2 skipped');
    await expect(page.locator('#backup-restore-result-list li')).toHaveCount(2);
    await expect(page.locator('#backup-restore-result-list li').nth(0)).toContainText('Missing Exercise A');
    await expect(page.locator('#backup-restore-result-list li').nth(1)).toContainText('Missing Exercise B');
  });

  test('sort by Name A-Z reorders the library', async ({ page }) => {
    const zebra = `Zebra ${Date.now()}`;
    const apple = `Apple ${Date.now()}`;
    const mango = `Mango ${Date.now()}`;

    await page.request.post('/api/backups', { data: { name: zebra } });
    await page.request.post('/api/backups', { data: { name: apple } });
    await page.request.post('/api/backups', { data: { name: mango } });

    await page.reload();
    await waitForPageReady(page);

    await page.locator('#backup-sort').selectOption('name-asc');

    const backupNames = page.locator('[data-role="backup-record"] .backup-record-name');
    const names = await backupNames.allTextContents();
    const appleIndex = names.indexOf(apple);
    const mangoIndex = names.indexOf(mango);
    const zebraIndex = names.indexOf(zebra);

    expect(appleIndex).toBeGreaterThanOrEqual(0);
    expect(mangoIndex).toBeGreaterThanOrEqual(0);
    expect(zebraIndex).toBeGreaterThanOrEqual(0);
    expect(appleIndex).toBeLessThan(mangoIndex);
    expect(mangoIndex).toBeLessThan(zebraIndex);
  });

  test('sort preference persists across reload', async ({ page }) => {
    await page.locator('#backup-sort').selectOption('oldest');
    await page.reload();
    await waitForPageReady(page);

    await expect(page.locator('#backup-sort')).toHaveValue('oldest');
  });

  test('saving with zero active exercises shows a warning and requires re-confirm', async ({ page }) => {
    const backupName = `Empty Snapshot ${Date.now()}`;

    await page.request.post('/clear_workout_plan', { failOnStatusCode: false });
    await page.reload();
    await waitForPageReady(page);

    const beforeResponse = await page.request.get('/api/backups');
    const beforeData = await beforeResponse.json();
    const beforeCount = Array.isArray(beforeData.data) ? beforeData.data.length : 0;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();

    await expect(page.locator('#backup-save-empty-warning')).toBeVisible();
    await expect(page.locator('#backup-center-save-submit')).toBeEnabled();

    const afterFirstResponse = await page.request.get('/api/backups');
    const afterFirstData = await afterFirstResponse.json();
    const afterFirstCount = Array.isArray(afterFirstData.data) ? afterFirstData.data.length : 0;
    expect(afterFirstCount).toBe(beforeCount);

    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await expect(page.locator('#backup-center-list')).toContainText(backupName);
    await expect(page.locator('#backup-save-empty-warning')).toBeHidden();
  });

  test('multi-line note renders with preserved line breaks', async ({ page }) => {
    const backupName = `Line Break Note ${Date.now()}`;
    const note = 'Line 1\nLine 2';

    await page.request.post('/api/backups', {
      data: {
        name: backupName,
        note,
      },
    });

    await page.reload();
    await waitForPageReady(page);
    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await expect(page.locator('#backup-detail-note')).toBeVisible();
    await expect(page.locator('#backup-detail-note')).toHaveJSProperty('textContent', note);
    await expect(page.locator('#backup-detail-note')).toHaveCSS('white-space', 'pre-wrap');
  });

  test('rename backup from detail panel persists on reload', async ({ page }) => {
    const backupName = `Rename E2E ${Date.now()}`;
    const renamedBackupName = `${backupName} After`;

    await page.locator('#backup-center-name').fill(backupName);
    await page.locator('#backup-center-save-submit').click();
    await expectToast(page, backupName);

    await page.locator('#backup-search').fill(backupName);
    await page.locator('[data-role="backup-record"]').filter({ hasText: backupName }).first().click();

    await page.locator('#backup-detail-edit-name').click();
    await page.locator('#backup-detail-name-input').fill(renamedBackupName);
    await page.locator('#backup-detail-name-save').click();
    await expectToast(page, 'Backup renamed successfully.');

    await page.reload();
    await waitForPageReady(page);
    await page.locator('#backup-search').fill(renamedBackupName);

    const renamedRecord = page.locator('[data-role="backup-record"]').filter({ hasText: renamedBackupName }).first();
    await expect(renamedRecord).toBeVisible();
    await expect(page.locator('#backup-center-list')).toContainText(renamedBackupName);
  });
});

test.describe('Program Backup API Integration', () => {
  test('GET /api/backups returns list', async ({ request }) => {
    const response = await request.get('/api/backups');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok === true || data.status === 'success' || data.success === true).toBeTruthy();
    expect(data).toHaveProperty('data');
    expect(Array.isArray(data.data)).toBe(true);
  });

  test('POST /api/backups creates backup', async ({ request }) => {
    const response = await request.post('/api/backups', {
      data: {
        name: 'API Test Backup ' + Date.now(),
        note: 'Created via E2E test'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok === true || data.status === 'success' || data.success === true).toBeTruthy();
    expect(data.data).toHaveProperty('id');
    expect(data.data).toHaveProperty('name');
  });

  test('POST /api/backups requires name', async ({ request }) => {
    const response = await request.post('/api/backups', {
      data: { note: 'No name provided' }
    });
    
    expect(response.ok()).toBeFalsy();
    expect(response.status()).toBe(400);
  });

  test('GET /api/backups/:id returns backup details', async ({ request }) => {
    // First create a backup
    const createResponse = await request.post('/api/backups', {
      data: { name: 'Detail Test ' + Date.now() }
    });
    const createData = await createResponse.json();

    if (createData.success && createData.data?.id) {
      const detailResponse = await request.get(`/api/backups/${createData.data.id}`);
      expect(detailResponse.ok()).toBeTruthy();
      
      const detailData = await detailResponse.json();
      expect(detailData.data).toHaveProperty('items');
    }
  });

  test('DELETE /api/backups/:id deletes backup', async ({ request }) => {
    // First create a backup
    const createResponse = await request.post('/api/backups', {
      data: { name: 'Delete Test ' + Date.now() }
    });
    const createData = await createResponse.json();

    if (createData.success && createData.data?.id) {
      const deleteResponse = await request.delete(`/api/backups/${createData.data.id}`);
      expect(deleteResponse.ok()).toBeTruthy();
    }
  });
});
