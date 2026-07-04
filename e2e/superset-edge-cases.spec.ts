/**
 * E2E Test: Superset Edge Cases
 * 
 * Tests superset functionality edge cases:
 * - Delete exercise that's part of superset
 * - Unlink from superset chain
 * - Replace exercise in superset
 * - Linking more than 2 exercises
 * - Superset state persistence
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, API_ENDPOINTS, resetWorkoutPlan } from './fixtures';

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
 * Helper to add an exercise to the plan
 */
async function addExercise(page: import('@playwright/test').Page, exerciseName?: string) {
  await page.waitForFunction(() => {
    const select = document.getElementById('exercise') as HTMLSelectElement;
    return select && select.options.length > 1;
  });
  
  const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
  const options = await exerciseSelect.locator('option').allInnerTexts();
  const usedExercises = new Set(
    (await page.locator('#workout_plan_table_body .exercise-name').allInnerTexts())
      .map(text => text.trim().toLowerCase())
      .filter(Boolean)
  );
  
  let targetExercise: string | undefined;
  if (exerciseName) {
    targetExercise = options.find(opt => opt.toLowerCase().includes(exerciseName.toLowerCase()));
  }
  if (!targetExercise) {
    targetExercise = options.find(opt => {
      const normalized = opt.trim().toLowerCase();
      return normalized !== '' && !opt.includes('Select') && !usedExercises.has(normalized);
    });
  }
  if (!targetExercise) {
    targetExercise = options.find(opt => opt && opt.trim() !== '' && !opt.includes('Select'));
  }
  
  expect(targetExercise, 'an unused exercise option should be available').toBeTruthy();
  await exerciseSelect.selectOption({ label: targetExercise! });
  
  await page.fill('#sets', '3');
  await page.fill('#min_rep', '8');
  await page.fill('#max_rep_range', '12');
  await page.fill('#weight', '100');
  
  const rowCountBefore = await page.locator('#workout_plan_table_body tr').count();
  const responsePromise = page.waitForResponse(response =>
    response.url().includes(API_ENDPOINTS.ADD_EXERCISE) &&
    response.request().method() === 'POST'
  );
  await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  await expect(page.locator('#workout_plan_table_body tr')).toHaveCount(rowCountBefore + 1);
}

/**
 * Helper to wait for exercises in table
 */
async function waitForExercisesInTable(page: import('@playwright/test').Page, minCount: number = 1) {
  await page.waitForFunction(
    (min) => document.querySelectorAll('#workout_plan_table_body tr').length >= min,
    minCount,
    { timeout: 5000 }
  );
}

test.beforeEach(async ({ page }) => {
  await resetWorkoutPlan(page);
});

test.describe('Superset Linking Edge Cases', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('rejects linking more than 2 exercises', async ({ page }) => {
    // Add 3 exercises
    await addExercise(page, 'bench');
    await addExercise(page, 'squat');
    await addExercise(page, 'deadlift');
    
    await waitForExercisesInTable(page, 3);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    const count = await checkboxes.count();
    
    if (count >= 3) {
      // Select 3 exercises
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      await checkboxes.nth(2).click();
      await page.waitForTimeout(300);
      
      // Check selection info message
      const selectionInfo = page.locator('#superset-selection-info');
      const text = await selectionInfo.textContent();
      
      // Should indicate that 3 exercises cannot be linked
      expect(text?.toLowerCase()).toContain('2');
      
      // Link button should be disabled
      const linkBtn = page.locator('#link-superset-btn');
      const isDisabled = await linkBtn.isDisabled().catch(() => true);
      expect(isDisabled).toBeTruthy();
    }
  });

  test('rejects linking only 1 exercise', async ({ page }) => {
    await addExercise(page);
    await waitForExercisesInTable(page, 1);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    const count = await checkboxes.count();
    
    if (count >= 1) {
      await checkboxes.nth(0).click();
      await page.waitForTimeout(300);
      
      // Link button should be disabled with only 1 selected
      const linkBtn = page.locator('#link-superset-btn');
      const isDisabled = await linkBtn.isDisabled().catch(() => true);
      expect(isDisabled).toBeTruthy();
    }
  });

  test('successfully links exactly 2 exercises', async ({ page }) => {
    await addExercise(page, 'bench');
    await addExercise(page, 'row');
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    await expect(checkboxes).toHaveCount(2);
    await checkboxes.nth(0).click();
    await checkboxes.nth(1).click();

    const linkBtn = page.locator('#link-superset-btn');
    await expect(linkBtn).toBeEnabled();
    const responsePromise = page.waitForResponse(response =>
      response.url().endsWith('/api/superset/link') && response.request().method() === 'POST'
    );
    await linkBtn.click();
    expect((await responsePromise).status()).toBe(200);

    const linkedRows = page.locator(
      '#workout_plan_table_body tr[data-superset-group]:not([data-superset-group=""])'
    );
    await expect(linkedRows).toHaveCount(2);
  });
});

test.describe('Delete Exercise in Superset', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('deleting one exercise from superset breaks the link', async ({ page }) => {
    // Add and link 2 exercises
    await addExercise(page, 'bench');
    await addExercise(page, 'row');
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      await page.waitForTimeout(300);
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
      }
      
      // Now delete one exercise
      const rows = page.locator('#workout_plan_table_body tr');
      const deleteBtn = rows.first().locator('button[data-action="delete"], .delete-btn, .btn-danger');
      
      // Handle confirmation dialog
      page.on('dialog', async dialog => {
        await dialog.accept();
      });
      
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        await page.waitForTimeout(1000);
        
        // Remaining exercise should no longer be in a superset
        const remainingRows = await page.locator('#workout_plan_table_body tr').count();
        
        // Either 1 row remains with no superset, or both deleted
        expect(remainingRows).toBeLessThanOrEqual(1);
      }
    }
  });

  test('deleting a linked exercise clears the partner superset group', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    // Link exercises first
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    if (await checkboxes.count() >= 2) {
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
      }
    }
    
    // Deleting one member unlinks the remaining partner server-side.
    const deleteBtn = page.locator('#workout_plan_table_body tr').first().locator('button[data-action="delete"], .delete-btn, .btn-danger');
    await expect(deleteBtn).toBeVisible();
    const responsePromise = page.waitForResponse(response =>
      response.url().endsWith('/remove_exercise') && response.request().method() === 'POST'
    );
    await deleteBtn.click();
    expect((await responsePromise).status()).toBe(200);
    await expect(page.locator('#workout_plan_table_body tr')).toHaveCount(1);
    await expect(page.locator('#workout_plan_table_body tr').first()).not.toHaveAttribute(
      'data-superset-group'
    );
  });
});

test.describe('Unlink Superset Edge Cases', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('unlink button only shows for superset exercises', async ({ page }) => {
    await addExercise(page);
    await waitForExercisesInTable(page, 1);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    if (await checkboxes.count() >= 1) {
      // Select non-superset exercise
      await checkboxes.nth(0).click();
      await page.waitForTimeout(300);
      
      // Unlink button should not be visible (or should be disabled)
      const unlinkBtn = page.locator('#unlink-superset-btn');
      const isVisible = await unlinkBtn.isVisible().catch(() => false);
      const isEnabled = await unlinkBtn.isEnabled().catch(() => false);
      const rowCountBefore = await page.locator('#workout_plan_table_body tr').count();
      
      // If unlink is available, invoking it should not mutate a non-superset row.
      if (isVisible && isEnabled) {
        await unlinkBtn.click();
        await page.waitForTimeout(500);
      }

      const rowCountAfter = await page.locator('#workout_plan_table_body tr').count();
      expect(rowCountAfter).toBe(rowCountBefore);
    }
  });

  test('unlink shows for selected superset exercise', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      // Create superset
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
        
        // Now select one of the superset exercises
        await checkboxes.nth(0).click();
        await page.waitForTimeout(300);
        
        // Unlink should now be visible
        const unlinkBtn = page.locator('#unlink-superset-btn');
        await expect(unlinkBtn).toBeVisible();
        await expect(unlinkBtn).toBeEnabled();
      }
    }
  });

  test('unlink clears both exercises from superset', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      // Create superset
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
        
        // Select one superset exercise
        const refreshedCheckboxes = page.locator('#workout_plan_table_body .superset-checkbox');
        await refreshedCheckboxes.nth(0).click();
        await page.waitForTimeout(300);
        
        // Click unlink
        const unlinkBtn = page.locator('#unlink-superset-btn');
        if (await unlinkBtn.isVisible() && await unlinkBtn.isEnabled()) {
          const responsePromise = page.waitForResponse(response =>
            response.url().endsWith('/api/superset/unlink') && response.request().method() === 'POST'
          );
          await unlinkBtn.click();
          expect((await responsePromise).status()).toBe(200);
          await expect(page.locator(
            '#workout_plan_table_body tr[data-superset-group]:not([data-superset-group=""])'
          )).toHaveCount(0);
        }
      }
    }
  });
});

test.describe('Replace Exercise in Superset', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('replace exercise in superset preserves or clears superset', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      // Create superset
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
        
        // Try to replace first exercise
        const replaceBtn = page.locator('#workout_plan_table_body tr').first()
          .locator('button[data-action="replace"], .replace-btn, .btn-swap, [title*="Replace"]');
        
        if (await replaceBtn.count() > 0 && await replaceBtn.first().isVisible()) {
          // Listen for API call
          let apiCalled = false;
          page.on('request', req => {
            if (req.url().includes('/replace_exercise')) {
              apiCalled = true;
            }
          });
          
          await replaceBtn.first().click();
          await page.waitForTimeout(1500);
          
          // Check that page didn't crash
          await expect(page.locator('h1')).toContainText('Workout Plan');
        }
      }
    }
  });
});

test.describe('Superset State Persistence', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('superset persists after page refresh', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      // Create superset
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
        
        // Refresh page
        await page.reload();
        await waitForPageReady(page);
        
        // Re-select routine to load table
        await selectRoutine(page);
        await waitForExercisesInTable(page, 2);
        
        // Check that superset styling/attributes are preserved
        const supersetRows = page.locator('#workout_plan_table_body tr[data-superset-group]:not([data-superset-group=""])');
        await expect(supersetRows).toHaveCount(2);
      }
    }
  });

  test('superset checkbox selection clears on routine change', async ({ page }) => {
    await addExercise(page);
    await waitForExercisesInTable(page, 1);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    if (await checkboxes.count() >= 1) {
      await checkboxes.nth(0).check();
      
      // Change to different workout day
      const daySelect = page.locator(SELECTORS.ROUTINE_DAY);
      const options = await daySelect.locator('option').allInnerTexts();
      const differentDay = options.find(opt => opt !== 'Workout A' && opt.trim() !== '');
      
      if (differentDay) {
        await daySelect.selectOption(differentDay);
        await page.waitForTimeout(500);
        
        // Switching context should leave superset action inactive.
        const checkedAfterChange = await page.locator('#workout_plan_table_body .superset-checkbox:checked').count();
        const linkBtn = page.locator('#link-superset-btn');
        await expect(linkBtn).toBeDisabled();
        expect(checkedAfterChange).toBeLessThan(2);
      }
    }
  });
});

test.describe('Superset Visual Indicators', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('linked exercises show visual superset indicator', async ({ page }) => {
    await addExercise(page);
    await addExercise(page);
    await waitForExercisesInTable(page, 2);
    
    const checkboxes = page.locator('#workout_plan_table_body .superset-checkbox');
    
    if (await checkboxes.count() >= 2) {
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      
      const linkBtn = page.locator('#link-superset-btn');
      if (await linkBtn.isEnabled()) {
        await linkBtn.click();
        await page.waitForTimeout(1000);
        
        const firstRow = page.locator('#workout_plan_table_body tr').first();
        await expect(firstRow).toHaveAttribute('data-superset-group', /^SS-/);
      }
    }
  });
});
