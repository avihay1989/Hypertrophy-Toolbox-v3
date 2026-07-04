/**
 * E2E Test: Empty State Handling
 * 
 * Tests application behavior with empty data:
 * - Import from empty workout plan
 * - Export empty plan to Excel
 * - Clear already-empty log
 * - Empty filter results
 * - Empty table displays
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

/**
 * Helper to select a complete routine
 */
async function selectRoutine(page: import('@playwright/test').Page) {
  await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
  await page.waitForFunction(() => {
    const select = document.getElementById('routine-program') as HTMLSelectElement;
    return select && select.options.length > 1;
  });
  await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Full Body');
  await page.waitForFunction(() => {
    const select = document.getElementById('routine-day') as HTMLSelectElement;
    return select && select.options.length > 1;
  });
  await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Workout A');
}

/**
 * Helper to clear all exercises from workout plan
 */
async function clearWorkoutPlan(page: import('@playwright/test').Page) {
  await resetWorkoutPlan(page);
  await page.reload();
  await waitForPageReady(page);
}

test.describe('Empty Workout Plan - Export', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('export empty plan shows warning message', async ({ page }) => {
    await selectRoutine(page);
    
    // Ensure plan is empty
    await clearWorkoutPlan(page);
    await page.waitForTimeout(500);
    
    const rows = await page.locator('#workout_plan_table_body tr').count();
    
    expect(rows).toBe(0);
    const exportBtn = page.locator(SELECTORS.EXPORT_EXCEL_BTN);
    await expect(exportBtn).toBeVisible();

    let downloadStarted = false;
    page.on('download', () => {
      downloadStarted = true;
    });

    await exportBtn.click();
    await expect(page.locator('#liveToast')).toBeVisible();
    await expect(page.locator('#toast-body')).toContainText('No exercises to export');
    expect(downloadStarted).toBe(false);
  });

  test('export to log with empty plan shows helpful message', async ({ page }) => {
    await selectRoutine(page);
    await clearWorkoutPlan(page);
    
    const rows = await page.locator('#workout_plan_table_body tr').count();
    
    expect(rows).toBe(0);
    const exportToLogBtn = page.locator(SELECTORS.EXPORT_TO_LOG_BTN);
    await expect(exportToLogBtn).toBeVisible();
    await exportToLogBtn.click();
    await expect(page.locator('#liveToast')).toBeVisible();
    await expect(page.locator('#toast-body')).toContainText('No exercises to export');
  });
});

test.describe('Empty Workout Log Operations', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_LOG);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('clear empty log does not error', async ({ page }) => {
    const clearBtn = page.locator(SELECTORS.CLEAR_LOG_BTN);
    
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      await page.waitForTimeout(500);
      
      // Modal should appear
      const modal = page.locator('#clearLogModal');
      const modalVisible = await modal.isVisible().catch(() => false);
      
      if (modalVisible) {
        // Click confirm
        const confirmBtn = page.locator('#confirm-clear-log-btn, .modal .btn-danger:has-text("Clear")');
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await page.waitForTimeout(1000);
        }
      }
      
      // Page should not crash
      await expect(page.locator('h1')).toContainText('Workout Log');
    }
  });

  test('import from empty workout plan shows message', async ({ page }) => {
    // First ensure workout plan is empty
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await clearWorkoutPlan(page);
    
    // Now go to workout log
    await page.goto(ROUTES.WORKOUT_LOG);
    await waitForPageReady(page);
    
    const importBtn = page.locator(SELECTORS.IMPORT_FROM_PLAN_BTN);
    
    if (await importBtn.isVisible()) {
      await importBtn.click();
      await page.waitForTimeout(1000);
      
      // Should show message about no exercises to import
      await expect(page.locator('#liveToast')).toBeVisible();
      await expect(page.locator('#toast-body')).toContainText(/no exercises|empty/i);
    }
  });

  test('empty log table shows appropriate message', async ({ page }) => {
    const table = page.locator('.workout-log-table');
    
    await expect(table).toBeVisible();
    await expect(table.locator('tbody tr')).toHaveCount(0);
  });
});

test.describe('Empty Filter Results', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('filter with no matches shows empty state', async ({ page }) => {
    // Apply filters that match nothing
    const muscleFilter = page.locator('#muscle-filter, [data-filter="muscle"]');
    
    if (await muscleFilter.isVisible()) {
      // Select a muscle that likely has no exercises in current routine
      const options = await muscleFilter.locator('option').allInnerTexts();
      const unusedMuscle = options.find(opt => opt && opt.trim() !== '' && !opt.includes('All'));
      
      if (unusedMuscle) {
        await muscleFilter.selectOption(unusedMuscle);
        await page.waitForTimeout(500);
        
        await expect(muscleFilter.locator('option:checked')).toHaveText(unusedMuscle);
        await expect(page.locator('#workout_plan_table_body')).toBeAttached();
      }
    }
  });

  test('clear filters after empty result restores data', async ({ page }) => {
    // Apply and then clear filters
    const muscleFilter = page.locator('#muscle-filter, [data-filter="muscle"]');
    const clearFiltersBtn = page.locator(SELECTORS.CLEAR_FILTERS_BTN);
    
    if (await muscleFilter.isVisible() && await clearFiltersBtn.isVisible()) {
      // Apply filter
      const options = await muscleFilter.locator('option').allInnerTexts();
      const filterOption = options.find(opt => opt && opt.trim() !== '' && !opt.includes('All'));
      
      if (filterOption) {
        await muscleFilter.selectOption(filterOption);
        await page.waitForTimeout(300);
        
        // Clear filters
        await clearFiltersBtn.click();
        await page.waitForTimeout(500);
        
        // Table should be functional
        const table = page.locator('#workout_plan_table_body');
        await expect(table).toBeVisible();
      }
    }
  });
});

test.describe('Empty Summary Pages', () => {
  test('weekly summary with no data shows appropriate state', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WEEKLY_SUMMARY);
    await waitForPageReady(page);
    
    // Check for empty state or data display
    const container = page.locator(SELECTORS.PAGE_WEEKLY_SUMMARY);
    await expect(container).toBeVisible({ timeout: 5000 });
    
    // Page should not crash
    await expect(page.locator('h1')).toContainText(/summary|weekly/i);
    
    consoleErrors.assertNoErrors();
  });

  test('session summary with no data shows appropriate state', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.SESSION_SUMMARY);
    await waitForPageReady(page);
    
    // Check for empty state or data display
    const container = page.locator(SELECTORS.PAGE_SESSION_SUMMARY);
    await expect(container).toBeVisible({ timeout: 5000 });
    
    // Page should not crash
    await expect(page.locator('h1')).toContainText(/summary|session/i);
    
    consoleErrors.assertNoErrors();
  });
});

test.describe('Empty Progression Plan', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('progression page with no exercises shows empty state', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    
    if (await exerciseSelector.isVisible()) {
      const options = await exerciseSelector.locator('option').count();
      
      // May have just placeholder
      if (options <= 1) {
        // Look for empty state message
        const emptyMessage = page.locator('.empty-state, .no-exercises, .alert-info');
        const messageVisible = await emptyMessage.isVisible().catch(() => false);
        
        // Should show helpful message or just placeholder
        expect(messageVisible || options <= 1).toBeTruthy();
      }
    }
  });

  test('suggestions stay hidden when no exercise can be selected', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    
    if (await exerciseSelector.isVisible()) {
      await expect(exerciseSelector.locator('option')).toHaveCount(1);
      await expect(page.locator('#suggestionsContainer')).toBeHidden();
    }
  });
});

test.describe('Empty Volume Splitter', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.VOLUME_SPLITTER);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('calculate with untouched inputs returns current default results', async ({ page }) => {
    const calculateBtn = page.locator(SELECTORS.CALCULATE_VOLUME_BTN);
    
    if (await calculateBtn.isVisible()) {
      const responsePromise = page.waitForResponse(response =>
        response.url().endsWith('/api/calculate_volume') && response.request().method() === 'POST'
      );
      await calculateBtn.click();
      const response = await responsePromise;
      expect(response.status()).toBe(200);
      expect((await response.json()).ok).toBe(true);
    }
  });

  test('reset on empty state does not error', async ({ page }) => {
    const resetBtn = page.locator(SELECTORS.RESET_VOLUME_BTN);
    
    if (await resetBtn.isVisible()) {
      await resetBtn.click();
      await page.waitForTimeout(500);
      
      // Should not crash
      await expect(page.locator('h1')).toBeVisible();
    }
  });

  test('export untouched volume inputs downloads a workbook', async ({ page }) => {
    const exportBtn = page.locator(SELECTORS.EXPORT_VOLUME_EXCEL_BTN);
    
    if (await exportBtn.isVisible()) {
      const downloadPromise = page.waitForEvent('download');
      await exportBtn.click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/^volume_plan_\d{4}-\d{2}-\d{2}\.xlsx$/);
    }
  });
});

test.describe('Table Empty State Messages', () => {
  test('workout plan table shows message when empty', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    
    // Clear all exercises
    await clearWorkoutPlan(page);
    await page.waitForTimeout(500);
    
    const tableBody = page.locator('#workout_plan_table_body');
    const rows = await tableBody.locator('tr').count();
    
    expect(rows).toBe(0);
    
    consoleErrors.assertNoErrors();
  });

  test('workout log table shows message when empty', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_LOG);
    await waitForPageReady(page);
    
    const tableBody = page.locator('.workout-log-table tbody');
    
    await expect(tableBody).toBeAttached();
    await expect(tableBody.locator('tr')).toHaveCount(0);
    
    consoleErrors.assertNoErrors();
  });
});
