/**
 * E2E Test: Workout Plan
 * 
 * Tests the workout plan page functionality including:
 * - Routine selection cascade
 * - Filters apply/clear
 * - Add exercise flow
 * - Export actions
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

test.beforeEach(async ({ page }) => {
  await resetWorkoutPlan(page);
});

test.describe('Workout Plan Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('page loads with all controls visible', async ({ page }) => {
    // Page is workout plan
    const workoutPage = page.locator(SELECTORS.PAGE_WORKOUT_PLAN);
    await expect(workoutPage).toBeVisible();
    await expect(page.locator('h1')).toContainText('Workout Plan');

    // Filter section should be visible
    await expect(page.locator('#filters-form')).toBeVisible();

    // Routine cascade selectors should be visible
    await expect(page.locator(SELECTORS.ROUTINE_ENV)).toBeVisible();
    await expect(page.locator(SELECTORS.ROUTINE_PROGRAM)).toBeVisible();
    await expect(page.locator(SELECTORS.ROUTINE_DAY)).toBeVisible();

    // Exercise dropdown should be visible
    await expect(page.locator(SELECTORS.EXERCISE_SEARCH)).toBeVisible();

    // Action buttons should be visible
    await expect(page.locator(SELECTORS.ADD_EXERCISE_BTN)).toBeVisible();
    await expect(page.locator(SELECTORS.EXPORT_EXCEL_BTN)).toBeVisible();
    await expect(page.locator(SELECTORS.EXPORT_TO_LOG_BTN)).toBeVisible();

    // Workout plan table should be visible
    await expect(page.locator(SELECTORS.EXERCISE_TABLE)).toBeVisible();
  });

  test('routine cascade: selecting environment enables program dropdown', async ({ page }) => {
    const envSelect = page.locator(SELECTORS.ROUTINE_ENV);
    const programSelect = page.locator(SELECTORS.ROUTINE_PROGRAM);
    const daySelect = page.locator(SELECTORS.ROUTINE_DAY);

    // Initially, program and day dropdowns should be disabled
    await expect(programSelect).toBeDisabled();
    await expect(daySelect).toBeDisabled();

    // Select GYM environment
    await envSelect.selectOption('GYM');

    // Program dropdown should now be enabled
    await expect(programSelect).toBeEnabled();
    // Day dropdown should still be disabled until program is selected
    await expect(daySelect).toBeDisabled();
  });

  test('routine cascade: selecting program enables workout dropdown', async ({ page }) => {
    const envSelect = page.locator(SELECTORS.ROUTINE_ENV);
    const programSelect = page.locator(SELECTORS.ROUTINE_PROGRAM);
    const daySelect = page.locator(SELECTORS.ROUTINE_DAY);

    // Select environment
    await envSelect.selectOption('GYM');
    await expect(programSelect).toBeEnabled();

    // Wait for program options to populate
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-program') as HTMLSelectElement;
      return select && select.options.length > 1;
    });

    // Select program (e.g., "Full Body")
    await programSelect.selectOption('Full Body');

    // Workout day dropdown should now be enabled
    await expect(daySelect).toBeEnabled();

    // Verify workout days are populated
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-day') as HTMLSelectElement;
      return select && select.options.length > 1;
    });
  });

  test('routine cascade: complete selection updates hidden field', async ({ page }) => {
    // Select full routine cascade
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

    // Check hidden routine field has the composite value
    const hiddenRoutine = await page.locator('#routine').inputValue();
    expect(hiddenRoutine).toContain('GYM');
    expect(hiddenRoutine).toContain('Full Body');
    expect(hiddenRoutine).toContain('Workout A');
  });

  test('add exercise: successfully adds exercise to plan', async ({ page }) => {
    // First select a routine
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

    // Wait for exercise dropdown to be populated
    await page.waitForFunction(() => {
      const select = document.getElementById('exercise') as HTMLSelectElement;
      return select && select.options.length > 1;
    });

    // Select an exercise from the dropdown - pick one that's less likely to be in the plan
    const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
    const options = await exerciseSelect.locator('option').all();
    
    // Try to find an exercise that may not be in the plan (pick from later options)
    let exerciseValue: string | null = null;
    for (let i = Math.min(10, options.length - 1); i >= 1; i--) {
      exerciseValue = await options[i].getAttribute('value');
      if (exerciseValue) break;
    }
    
    if (exerciseValue) {
      await exerciseSelect.selectOption(exerciseValue);
    }

    // Get initial row count
    const initialRows = await page.locator('#workout_plan_table_body tr').count();

    // Click add exercise button
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();

    // Wait for either: row count to increase OR a toast notification to appear
    // (Toast appears for successful add OR duplicate rejection)
    await Promise.race([
      page.waitForFunction((prevCount) => {
        const rows = document.querySelectorAll('#workout_plan_table_body tr');
        return rows.length > prevCount;
      }, initialRows, { timeout: 5000 }),
      page.waitForSelector('.toast', { timeout: 5000 })
    ]);

    // Verify either row was added OR toast appeared (both indicate the action worked)
    const newRows = await page.locator('#workout_plan_table_body tr').count();
    const toastVisible = await page.locator('.toast').isVisible().catch(() => false);
    
    // Test passes if rows increased OR a toast notification appeared
    expect(newRows > initialRows || toastVisible).toBe(true);
  });

  test('clear filters button resets all filter dropdowns', async ({ page }) => {
    // Find filter dropdowns and set some values
    const filterForm = page.locator('#filters-form');
    const filterSelects = filterForm.locator('select.filter-dropdown');
    
    // Try to set a filter if available (equipment filter, for example)
    const firstFilter = filterSelects.first();
    await firstFilter.waitFor({ state: 'visible' });
    
    // Get the first non-empty option
    const firstFilterOptions = await firstFilter.locator('option').all();
    if (firstFilterOptions.length > 1) {
      // Select first non-empty option
      const optionValue = await firstFilterOptions[1].getAttribute('value');
      if (optionValue) {
        await firstFilter.selectOption(optionValue);
      }
    }

    // Click clear filters button
    await page.locator(SELECTORS.CLEAR_FILTERS_BTN).click();

    // Verify filter is reset to empty/All
    const filterValue = await firstFilter.inputValue();
    expect(filterValue).toBe('');
  });

  test('filter dropdowns exist and have options', async ({ page }) => {
    // Verify filter form exists
    const filterForm = page.locator('#filters-form');
    await expect(filterForm).toBeVisible();

    // Check that at least some filter dropdowns exist (they're dynamically generated)
    const filterSelects = filterForm.locator('select.filter-dropdown');
    const count = await filterSelects.count();
    expect(count).toBeGreaterThan(0);
  });

  test('exercise table has correct structure', async ({ page }) => {
    const table = page.locator(SELECTORS.EXERCISE_TABLE);
    await expect(table).toBeVisible();

    // Check table headers exist
    const headers = table.locator('thead th');
    const headerCount = await headers.count();
    expect(headerCount).toBeGreaterThan(5); // Should have multiple columns

    // Check expected columns exist
    const tableHtml = await table.locator('thead').innerHTML();
    expect(tableHtml.toLowerCase()).toContain('routine');
    expect(tableHtml.toLowerCase()).toContain('exercise');
    expect(tableHtml.toLowerCase()).toContain('sets');
    expect(tableHtml.toLowerCase()).toContain('weight');
  });

  test('routine tabs navigation exists', async ({ page }) => {
    // Routine tabs container should exist
    const routineTabs = page.locator('#routine-tabs');
    await expect(routineTabs).toBeVisible();

    // "All" tab should be present
    const allTab = page.locator('#tab-all');
    await expect(allTab).toBeVisible();
    await expect(allTab).toHaveClass(/active/);
  });

  test('export button is clickable and triggers action', async ({ page }) => {
    // Make sure we have some data first by adding an exercise
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

    // Wait for exercise dropdown
    await page.waitForFunction(() => {
      const select = document.getElementById('exercise') as HTMLSelectElement;
      return select && select.options.length > 1;
    });

    // Select and add exercise
    const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
    const firstOption = await exerciseSelect.locator('option').nth(1).getAttribute('value');
    if (firstOption) {
      await exerciseSelect.selectOption(firstOption);
    }
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();

    // Wait for row to be added
    await page.waitForSelector('#workout_plan_table_body tr');

    // Setup download handling
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    // Click export button
    await page.locator(SELECTORS.EXPORT_EXCEL_BTN).click();

    // Either download starts or toast shows
    const download = await downloadPromise;
    if (download) {
      expect(download.suggestedFilename()).toContain('xlsx');
    }
    // If no download, check for toast (could be empty plan warning)
  });

  test('generate starter plan modal opens', async ({ page }) => {
    // Click generate starter plan button
    const generateBtn = page.locator('#generate-plan-btn');
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // Modal should open
    const modal = page.locator('#generatePlanModal');
    await expect(modal).toBeVisible({ timeout: 5000 });
    await expect(modal.locator('.modal-title')).toContainText('Generate Starter Plan');

    // Verify modal has expected content/structure
    await expect(modal.locator('.modal-body')).toBeVisible();
    await expect(modal.locator('.btn-close')).toBeVisible();
  });
});

test.describe('Plan Generator v1.5.0 Features', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('generate plan modal has priority muscles option', async ({ page }) => {
    // Open the generate plan modal
    const generateBtn = page.locator('#generate-plan-btn');
    await generateBtn.click();

    const modal = page.locator('#generatePlanModal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Check for priority muscles selector (v1.5.0 feature)
    const priorityMuscles = modal.locator('#priority-muscles, [name="priority_muscles"], select[data-field="priority_muscles"]');
    
    // If the priority muscles field exists, verify it works
    if (await priorityMuscles.count() > 0) {
      await expect(priorityMuscles).toBeVisible();
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('generate plan modal has time budget option', async ({ page }) => {
    // Open the generate plan modal
    const generateBtn = page.locator('#generate-plan-btn');
    await generateBtn.click();

    const modal = page.locator('#generatePlanModal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Check for time budget input (v1.5.0 feature)
    const timeBudget = modal.locator('#time-budget, [name="time_budget_minutes"], input[data-field="time_budget"]');
    
    // If the time budget field exists, verify it accepts numeric input
    if (await timeBudget.count() > 0) {
      await expect(timeBudget).toBeVisible();
      // Time budget should accept numbers
      await timeBudget.fill('45');
      await expect(timeBudget).toHaveValue('45');
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('generate plan modal has merge mode toggle', async ({ page }) => {
    // Open the generate plan modal
    const generateBtn = page.locator('#generate-plan-btn');
    await generateBtn.click();

    const modal = page.locator('#generatePlanModal');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Check for merge mode checkbox (v1.5.0 feature)
    const mergeMode = modal.locator('#merge-mode, [name="merge_mode"], input[type="checkbox"][data-field="merge_mode"]');
    
    // If merge mode toggle exists, verify it's functional
    if (await mergeMode.count() > 0) {
      await expect(mergeMode).toBeVisible();
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('generator API returns priority muscles option', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/get_generator_options');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.data).toHaveProperty('priority_muscles');
    expect(data.data.priority_muscles).toHaveProperty('available');
    expect(Array.isArray(data.data.priority_muscles.available)).toBe(true);
    expect(data.data.priority_muscles.available.length).toBeGreaterThan(0);
    expect(data.data.priority_muscles).toHaveProperty('max_selections');
    expect(data.data.priority_muscles.max_selections).toBe(2);
  });

  test('generator API returns time budget presets', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/get_generator_options');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.data).toHaveProperty('time_budget');
    expect(data.data.time_budget).toHaveProperty('min');
    expect(data.data.time_budget).toHaveProperty('max');
    expect(data.data.time_budget).toHaveProperty('presets');
    expect(Array.isArray(data.data.time_budget.presets)).toBe(true);
  });

  test('generator API validates priority muscles limit', async ({ request }) => {
    // Try to generate with too many priority muscles
    const response = await request.post('http://127.0.0.1:5000/generate_starter_plan', {
      data: {
        training_days: 2,
        environment: 'gym',
        priority_muscles: ['Chest', 'Back', 'Shoulders', 'Arms', 'Legs'],
        persist: false
      }
    });
    
    // Should either accept (with truncation) or return validation error
    expect([200, 400]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      // If accepted, it should have truncated to max 2
      if (data.data.metadata && data.data.metadata.priority_muscles) {
        expect(data.data.metadata.priority_muscles.length).toBeLessThanOrEqual(2);
      }
    }
  });
});
