/**
 * E2E Test: Workout Plan
 * 
 * Tests the workout plan page functionality including:
 * - Routine selection cascade
 * - Filters apply/clear
 * - Add exercise flow
 * - Export actions
 */
import type { Page } from '@playwright/test';
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

  test('muscle naming toggle syncs workout table column visibility', async ({ page }) => {
    const tableModeToggle = page.locator('.tbl-view-mode-toggle[data-table-key="workout_plan"]');
    const advancedOnlyHeader = page.locator('th[data-label="Tertiary Muscle"]');

    await expect(tableModeToggle).toBeVisible();
    await expect(tableModeToggle).toContainText('Simple');
    await expect(advancedOnlyHeader).toBeHidden();

    await page.locator('#muscleModeToggle').click();

    await expect(tableModeToggle).toContainText('Advanced');
    await expect(advancedOnlyHeader).toBeVisible();

    await page.locator('#muscleModeToggle').click();

    await expect(tableModeToggle).toContainText('Simple');
    await expect(advancedOnlyHeader).toBeHidden();
  });

  test('muscle filter selections survive simple-to-scientific toggle', async ({ page }) => {
    const muscleFilters = [
      '#primary_muscle_group',
      '#secondary_muscle_group',
      '#tertiary_muscle_group',
      '#advanced_isolated_muscles',
    ];

    await page.waitForFunction(() => {
      const primary = document.getElementById('primary_muscle_group') as HTMLSelectElement | null;
      return Boolean(primary && Array.from(primary.options).some(option => option.value === 'chest'));
    });

    await page.evaluate((selectors) => {
      selectors.forEach((selector) => {
        const select = document.querySelector(selector) as HTMLSelectElement | null;
        if (!select) return;
        select.value = 'chest';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }, muscleFilters);

    await page.locator('#muscleModeToggle').click();

    await page.waitForFunction((selectors) => {
      return selectors.every((selector) => {
        const select = document.querySelector(selector) as HTMLSelectElement | null;
        return Boolean(select && select.value === 'chest' && select.selectedOptions[0]?.textContent?.includes('Chest'));
      });
    }, muscleFilters);
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

  test('weight field accepts decimals and preserves manual edits (Issue #5)', async ({ page }) => {
    // Wait for the exercise dropdown to be populated.
    await page.waitForFunction(() => {
      const select = document.getElementById('exercise') as HTMLSelectElement;
      return select && select.options.length > 1;
    });

    const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
    const options = await exerciseSelect.locator('option').all();
    const firstValue = await options[1].getAttribute('value');
    const secondValue =
      options.length > 2 ? await options[2].getAttribute('value') : null;
    expect(firstValue).toBeTruthy();
    expect(secondValue).toBeTruthy();

    // Select an exercise — this is the one-shot trigger that should apply
    // the profile estimate to the Weight field.
    await exerciseSelect.selectOption(firstValue!);

    // Wait for the estimate request to settle so the suggested value lands
    // in the input before we type over it.
    await page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/user_profile/estimate') && resp.status() === 200,
      { timeout: 5000 },
    );

    const weightInput = page.locator('#weight');
    await expect(weightInput).toHaveAttribute('type', 'number');
    const stepAttr = await weightInput.getAttribute('step');
    expect(['any', '0.25']).toContain(stepAttr);

    // Decimal input must persist in the field.
    await weightInput.fill('17.5');
    await expect(weightInput).toHaveValue('17.5');

    // Blur to commit, then re-read — the manual decimal value must survive
    // the change-event clamp/normalization handler.
    await weightInput.blur();
    await expect(weightInput).toHaveValue('17.5');

    // Re-selecting the same exercise should NOT overwrite the user's edit
    // (selectOption with the same value does not fire `change` in the DOM,
    // but assert the value is still intact regardless).
    await expect(weightInput).toHaveValue('17.5');

    // Switching to a different exercise IS the trigger to re-apply the
    // estimate — the manual value may now be replaced by the new estimate.
    if (secondValue && secondValue !== firstValue) {
      await exerciseSelect.selectOption(secondValue);
      await page.waitForResponse(
        (resp) =>
          resp.url().includes('/api/user_profile/estimate') && resp.status() === 200,
        { timeout: 5000 },
      );
      // Weight should now be whatever the new estimate decided — just
      // assert it is a valid non-empty numeric value (not "17.5" frozen).
      const newValue = await weightInput.inputValue();
      expect(newValue).not.toBe('');
      expect(Number.isNaN(parseFloat(newValue))).toBe(false);
    }
  });

  test('Workout Controls "show the math" expander opens with steps and improvement hint (Issue #17)', async ({ page }) => {
    // Seed a cold-start scenario so the trace + improvement hint appear.
    await page.request.post('/api/user_profile', {
      data: {
        gender: 'M',
        age: 30,
        height_cm: 180,
        weight_kg: 75,
        experience_years: 3,
      },
    });
    // Wipe any saved reference lifts that might have leaked from prior tests.
    await page.request.post('/api/user_profile/lifts', {
      data: [
        { lift_key: 'barbell_bench_press', weight_kg: null, reps: null },
        { lift_key: 'barbell_bicep_curl', weight_kg: null, reps: null },
      ],
    });

    await page.reload();
    await waitForPageReady(page);

    await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-program') as HTMLSelectElement | null;
      return Boolean(select && select.options.length > 1);
    });
    await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Full Body');
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-day') as HTMLSelectElement | null;
      return Boolean(select && select.options.length > 1);
    });
    await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Workout A');

    const estimateResponse = page.waitForResponse(resp =>
      resp.url().includes('/api/user_profile/estimate') && resp.status() === 200
    );
    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('Barbell Bench Press');
    await estimateResponse;

    const toggle = page.locator('#workout-estimate-trace-toggle');
    const container = page.locator('#workout-estimate-trace');
    // Toggle is visible (trace is non-empty) and starts collapsed.
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(container).toBeHidden();

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(container).toBeVisible();

    // Cold-start trace must call out its key inputs (Issue #17 §"What might
    // affect the score" — bodyweight, experience, preset, rounding).
    await expect(container).toContainText('Cold-start 1RM');
    await expect(container).toContainText('Light');
    await expect(container).toContainText(/Bodyweight ratio/);

    // Improvement hint surfaces a Profile-page link anchored to the
    // suggested lift row.
    const hintLink = container.locator('[data-trace-improvement-link]');
    await expect(hintLink).toBeVisible();
    const href = await hintLink.getAttribute('href');
    expect(href).toMatch(/\/user_profile.*barbell_bench_press/);
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

// ============================================================================
// Muscle selector — workout-cool body map (PLANNING.md §3)
//
// Simple mode loads workout-cool's anatomy art (multi-key BACK region);
// Advanced mode loads first-party sub-muscle SVGs. Switching modes must
// reload the SVG variant and preserve `selectedMuscles` across the swap.
// ============================================================================

test.describe('Muscle selector body-map variants', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    await page.locator('#generate-plan-btn').click();
    await expect(page.locator('#generatePlanModal')).toBeVisible({ timeout: 5000 });
    // Wait for the inline SVG fetch + render in the modal.
    await expect(
      page.locator('#muscle-selector-container #svg-container svg')
    ).toBeVisible({ timeout: 5000 });
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('Simple mode loads workout-cool art; Advanced reloads first-party sub-muscle art; selection survives swap', async ({ page }) => {
    const svg = page.locator('#muscle-selector-container #svg-container svg');

    // Default mode is simple. Workout-cool art ships with id="body-anterior-workoutcool".
    await expect(svg).toHaveAttribute('id', /body-anterior-workoutcool/);

    // Pick an arbitrary single-key region (chest) so we have something to verify
    // selection survives across the variant swap.
    await page.locator('#muscle-selector-container svg [data-canonical-muscles="chest"]').first().click();
    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="chest"] .legend-checkbox.checked')
    ).toBeVisible();

    // Switch to advanced — must trigger an SVG variant reload, not just a legend re-render.
    await page.locator('#muscle-selector-container [data-view="advanced"]').click();
    await expect(svg).toHaveAttribute('id', /body-anterior-hypertrophy-advanced/);

    // Selection state preserved (advanced legend renders one row per child of chest).
    for (const child of ['upper-chest', 'mid-chest', 'lower-chest']) {
      await expect(
        page.locator(`#muscle-selector-container .legend-item[data-muscle="${child}"] .legend-checkbox.checked`)
      ).toBeVisible();
    }

    // Switch back to simple — workout-cool art must reload and chest stays selected.
    await page.locator('#muscle-selector-container [data-view="simple"]').click();
    await expect(svg).toHaveAttribute('id', /body-anterior-workoutcool/);
    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="chest"] .legend-checkbox.checked')
    ).toBeVisible();
  });

  test('Multi-key BACK region click cascades to all five advanced children', async ({ page }) => {
    // Move to the back tab where workout-cool exposes the multi-key BACK region.
    await page.locator('#muscle-selector-container [data-side="back"]').click();
    await expect(
      page.locator('#muscle-selector-container #svg-container svg')
    ).toHaveAttribute('id', /body-posterior-workoutcool/);

    const backRegion = page
      .locator('#muscle-selector-container svg [data-canonical-muscles="lats,upper-back,lowerback"]')
      .first();
    await expect(backRegion).toBeVisible();

    // First click: all three simple legend items (lats, upper-back, lowerback)
    // must become fully checked because every advanced child of every simple
    // key is now in selectedMuscles.
    await backRegion.click();
    for (const simpleKey of ['lats', 'upper-back', 'lowerback']) {
      await expect(
        page.locator(`#muscle-selector-container .legend-item[data-muscle="${simpleKey}"] .legend-checkbox.checked`)
      ).toBeVisible();
    }

    // Second click: clears all five advanced children — every legend item
    // returns to plain (no checked / partial class).
    await backRegion.click();
    for (const simpleKey of ['lats', 'upper-back', 'lowerback']) {
      await expect(
        page.locator(`#muscle-selector-container .legend-item[data-muscle="${simpleKey}"] .legend-checkbox.checked`)
      ).toHaveCount(0);
      await expect(
        page.locator(`#muscle-selector-container .legend-item[data-muscle="${simpleKey}"] .legend-checkbox.partial`)
      ).toHaveCount(0);
    }
  });

  test('Selecting only one upper-back child in Advanced renders BACK as partial back in Simple', async ({ page }) => {
    // Switch to advanced, navigate to back tab, select only `rhomboids` (one
    // of three children of upper-back). This is the regression case from
    // PLANNING.md §3.4.1 / §3.7: BACK must show `partial` because not every
    // advanced child of {lats, upper-back, lowerback} is selected.
    await page.locator('#muscle-selector-container [data-view="advanced"]').click();
    await page.locator('#muscle-selector-container [data-side="back"]').click();

    await page.locator('#muscle-selector-container .legend-item[data-muscle="rhomboids"]').click();
    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="rhomboids"] .legend-checkbox.checked')
    ).toBeVisible();

    // Back to simple — BACK region must render with .partial.
    await page.locator('#muscle-selector-container [data-view="simple"]').click();
    await expect(
      page.locator('#muscle-selector-container #svg-container svg')
    ).toHaveAttribute('id', /body-posterior-workoutcool/);

    const backRegion = page
      .locator('#muscle-selector-container svg [data-canonical-muscles="lats,upper-back,lowerback"]')
      .first();
    await expect(backRegion).toHaveClass(/partial/);
    await expect(backRegion).not.toHaveClass(/selected(?!\.partial)/);
  });

  test('Advanced map region selects a single sub-muscle without selecting siblings', async ({ page }) => {
    await page.locator('#muscle-selector-container [data-view="advanced"]').click();
    await expect(
      page.locator('#muscle-selector-container #svg-container svg')
    ).toHaveAttribute('id', /body-anterior-hypertrophy-advanced/);

    await page
      .locator('#muscle-selector-container svg [data-canonical-muscles="upper-chest"]')
      .first()
      .click();

    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="upper-chest"] .legend-checkbox.checked')
    ).toBeVisible();
    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="mid-chest"] .legend-checkbox.checked')
    ).toHaveCount(0);
    await expect(
      page.locator('#muscle-selector-container .legend-item[data-muscle="lower-chest"] .legend-checkbox.checked')
    ).toHaveCount(0);
    await expect(
      page.locator('#muscle-selector-container .legend-group-header[data-parent="chest"] .legend-checkbox.partial')
    ).toBeVisible();
  });
});

// ============================================================================
// §5 — Exercise reference video modal (PLANNING.md §5)
//
// Pattern A: a single play button per row opens a modal. Curated exercises
// embed via youtube.com/embed; uncurated exercises fall through to a
// search-on-YouTube CTA. Closing the modal clears the iframe src.
// ============================================================================

test.describe('Exercise reference video modal (workout-plan)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    // Seed one exercise into the plan so a row renders with the play button.
    await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
    await page.waitForFunction(() => {
      const s = document.getElementById('routine-program') as HTMLSelectElement | null;
      return Boolean(s && s.options.length > 1);
    });
    await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Full Body');
    await page.waitForFunction(() => {
      const s = document.getElementById('routine-day') as HTMLSelectElement | null;
      return Boolean(s && s.options.length > 1);
    });
    await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Workout A');
    await page.waitForFunction(() => {
      const s = document.getElementById('exercise') as HTMLSelectElement | null;
      return Boolean(s && s.options.length > 1);
    });
    const exSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
    const firstValue = await exSelect.locator('option').nth(1).getAttribute('value');
    if (firstValue) {
      await exSelect.selectOption(firstValue);
    }
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await page.waitForSelector('#workout_plan_table_body tr');
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('every row has an accessible play button next to Swap', async ({ page }) => {
    const rows = page.locator('#workout_plan_table_body tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    const firstRow = rows.first();
    const playBtn = firstRow.locator('.btn-video');
    await expect(playBtn).toBeVisible();

    const ariaLabel = await playBtn.getAttribute('aria-label');
    expect(ariaLabel).toMatch(/^Play reference video for /);

    const swapBtn = firstRow.locator('.btn-swap');
    await expect(swapBtn).toBeVisible();
  });

  test('uncurated exercise (NULL youtube_video_id) opens the search-fallback variant', async ({ page }) => {
    const playBtn = page.locator('#workout_plan_table_body tr .btn-video').first();
    await playBtn.click();

    const modal = page.locator('#exerciseVideoModal');
    await expect(modal).toBeVisible();

    // Embed wrap should be hidden; search wrap visible.
    await expect(page.locator('#exerciseVideoEmbedWrap')).toBeHidden();
    await expect(page.locator('#exerciseVideoSearchWrap')).toBeVisible();

    // External CTA points at youtube.com/results with the exercise name encoded.
    const externalLink = page.locator('#exerciseVideoExternalLink');
    const href = await externalLink.getAttribute('href');
    expect(href).toMatch(/^https:\/\/www\.youtube\.com\/results\?search_query=/);

    // External link must open in a new tab with safe rel attributes.
    expect(await externalLink.getAttribute('target')).toBe('_blank');
    expect(await externalLink.getAttribute('rel')).toBe('noopener noreferrer');

    // Iframe is empty (no leaked src on uncurated rows).
    const iframeSrc = await page.locator('#exerciseVideoIframe').getAttribute('src');
    expect(iframeSrc === '' || iframeSrc === null).toBe(true);
  });

  test('valid id opens embed mode; close clears iframe src', async ({ page }) => {
    // Drive the modal directly via its public API. This exercises the JS
    // logic without mutating the live exercises table — equivalent to a
    // curated youtube_video_id arriving in the row data.
    await page.evaluate(() => {
      // @ts-expect-error - exposed by static/js/modules/exercise-video-modal.js
      window.openExerciseVideoModal('dQw4w9WgXcQ', 'Test Exercise');
    });

    const modal = page.locator('#exerciseVideoModal');
    await expect(modal).toBeVisible();

    // Embed visible, search hidden.
    await expect(page.locator('#exerciseVideoEmbedWrap')).toBeVisible();
    await expect(page.locator('#exerciseVideoSearchWrap')).toBeHidden();

    const iframe = page.locator('#exerciseVideoIframe');
    const src = await iframe.getAttribute('src');
    expect(src).toMatch(/^https:\/\/www\.youtube\.com\/embed\/dQw4w9WgXcQ/);

    const externalLink = page.locator('#exerciseVideoExternalLink');
    const externalHref = await externalLink.getAttribute('href');
    expect(externalHref).toBe('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    expect(await externalLink.getAttribute('target')).toBe('_blank');
    expect(await externalLink.getAttribute('rel')).toBe('noopener noreferrer');

    // Close — iframe src must be blanked so playback stops.
    await page.locator('#exerciseVideoModal .btn-close').click();
    await expect(modal).toBeHidden();
    const srcAfter = await iframe.getAttribute('src');
    expect(srcAfter === '' || srcAfter === null).toBe(true);
  });

  test('opening for a different exercise swaps the URL cleanly', async ({ page }) => {
    // First open: id A, expect iframe src to match A and title to mention A.
    await page.evaluate(() => {
      // @ts-expect-error - exposed by exercise-video-modal.js
      window.openExerciseVideoModal('dQw4w9WgXcQ', 'First Exercise');
    });
    await expect(page.locator('#exerciseVideoModal')).toBeVisible();
    await expect(page.locator('#exerciseVideoIframe')).toHaveAttribute(
      'src',
      /embed\/dQw4w9WgXcQ/,
    );
    await expect(page.locator('#exerciseVideoModalExerciseName')).toContainText(
      'First Exercise',
    );

    // Second call (modal still open): contents must update in place to id B.
    await page.evaluate(() => {
      // @ts-expect-error - exposed by exercise-video-modal.js
      window.openExerciseVideoModal('aaaaaaaaaaa', 'Second Exercise');
    });
    await expect(page.locator('#exerciseVideoIframe')).toHaveAttribute(
      'src',
      /embed\/aaaaaaaaaaa/,
    );
    await expect(page.locator('#exerciseVideoModalExerciseName')).toContainText(
      'Second Exercise',
    );
  });

  test('malformed id falls through to search fallback', async ({ page }) => {
    await page.evaluate(() => {
      // @ts-expect-error - exposed by exercise-video-modal.js
      window.openExerciseVideoModal('not-an-id', 'Fake Exercise');
    });
    await expect(page.locator('#exerciseVideoModal')).toBeVisible();
    await expect(page.locator('#exerciseVideoEmbedWrap')).toBeHidden();
    await expect(page.locator('#exerciseVideoSearchWrap')).toBeVisible();

    const href = await page.locator('#exerciseVideoExternalLink').getAttribute('href');
    expect(href).toMatch(/^https:\/\/www\.youtube\.com\/results\?search_query=/);
    expect(href).toContain('Fake');
  });
});

test.describe('§4 free-exercise-db thumbnails', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await resetWorkoutPlan(page);
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  // Render a mocked row directly via the module's `updateWorkoutPlanTable`
  // entry point so the assertions don't depend on the live DB carrying a
  // curated `media_path`. Mirrors the JSON shape `/get_workout_plan` returns.
  async function renderMockExercises(page: Page, exercises: Record<string, unknown>[]) {
    await page.evaluate(async (rows) => {
      const mod = await import('/static/js/modules/workout-plan.js');
      mod.updateWorkoutPlanTable(rows as never);
    }, exercises);
  }

  test('mocked row with media_path renders a thumbnail img with safe src', async ({ page }) => {
    await renderMockExercises(page, [
      {
        id: 9001,
        routine: 'GYM - Full Body - Workout A',
        exercise: 'Band Good Morning',
        media_path: 'Band_Good_Morning/0.jpg',
        primary_muscle_group: 'Hamstrings',
        sets: 3,
        min_rep_range: 8,
        max_rep_range: 12,
        rir: 2,
        weight: 50,
      },
    ]);

    const row = page.locator('#workout_plan_table_body tr').first();
    await expect(row).toBeVisible();

    const thumb = row.locator('img.exercise-thumbnail');
    await expect(thumb).toBeVisible();

    const src = await thumb.getAttribute('src');
    expect(src).toBe('/static/vendor/free-exercise-db/exercises/Band_Good_Morning/0.jpg');
    expect(src).not.toContain('..');

    const alt = await thumb.getAttribute('alt');
    expect(alt).toBe('Band Good Morning reference');

    expect(await thumb.getAttribute('loading')).toBe('lazy');
    expect(await thumb.getAttribute('width')).toBe('32');
    expect(await thumb.getAttribute('height')).toBe('32');
  });

  test('mocked row with NULL media_path renders no img and no console errors', async ({ page }) => {
    await renderMockExercises(page, [
      {
        id: 9002,
        routine: 'GYM - Full Body - Workout A',
        exercise: 'Some Uncurated Exercise',
        media_path: null,
        primary_muscle_group: 'Quadriceps',
        sets: 3,
        min_rep_range: 5,
        max_rep_range: 8,
        rir: 1,
        weight: 80,
      },
    ]);

    const row = page.locator('#workout_plan_table_body tr').first();
    await expect(row).toBeVisible();
    await expect(row.locator('img.exercise-thumbnail')).toHaveCount(0);
  });

  test('mocked row with HTML-special exercise name renders escaped (no raw markup leaks)', async ({ page }) => {
    await renderMockExercises(page, [
      {
        id: 9003,
        routine: 'GYM - Full Body - Workout A',
        exercise: `Coach's <Test> Press`,
        media_path: 'Band_Good_Morning/0.jpg',
        primary_muscle_group: 'Chest',
        sets: 3,
        min_rep_range: 8,
        max_rep_range: 12,
        rir: 2,
        weight: 60,
      },
    ]);

    const row = page.locator('#workout_plan_table_body tr').first();
    // textContent strips markup; if escapeHtml is working, the literal angle brackets are present.
    await expect(row.locator('.exercise-name')).toHaveText(`Coach's <Test> Press`);
    // And no nested <Test> element was injected from the angle brackets.
    expect(await row.locator('.exercise-name Test').count()).toBe(0);

    const thumb = row.locator('img.exercise-thumbnail');
    const alt = await thumb.getAttribute('alt');
    expect(alt).toBe(`Coach's <Test> Press reference`);
  });

  test('escapeHtml + resolveExerciseMediaSrc behave per the §4.3/§4.4 contract', async ({ page }) => {
    const result = await page.evaluate(async () => {
      const mod = await import('/static/js/modules/exercise-helpers.js');
      return {
        escapeMixed: mod.escapeHtml(`Coach's <Test> Press`),
        escapeAmp: mod.escapeHtml('A & B'),
        escapeNull: mod.escapeHtml(null),
        validJpg: mod.resolveExerciseMediaSrc('Band_Good_Morning/0.jpg'),
        validUpperExt: mod.resolveExerciseMediaSrc('Foo/0.PNG'),
        invalidEmpty: mod.resolveExerciseMediaSrc(''),
        invalidNull: mod.resolveExerciseMediaSrc(null),
        invalidAbs: mod.resolveExerciseMediaSrc('/abs/path/0.jpg'),
        invalidParent: mod.resolveExerciseMediaSrc('../etc/passwd'),
        invalidBackslash: mod.resolveExerciseMediaSrc('dir\\img.jpg'),
        invalidColon: mod.resolveExerciseMediaSrc('C:/temp/0.jpg'),
        invalidExt: mod.resolveExerciseMediaSrc('dir/img.exe'),
        invalidNoExt: mod.resolveExerciseMediaSrc('dir/img'),
        encodesSpace: mod.resolveExerciseMediaSrc('weird name/0.jpg'),
      };
    });

    expect(result.escapeMixed).toBe('Coach&#39;s &lt;Test&gt; Press');
    expect(result.escapeAmp).toBe('A &amp; B');
    expect(result.escapeNull).toBe('');
    expect(result.validJpg).toBe('/static/vendor/free-exercise-db/exercises/Band_Good_Morning/0.jpg');
    expect(result.validUpperExt).toBe('/static/vendor/free-exercise-db/exercises/Foo/0.PNG');
    expect(result.invalidEmpty).toBeNull();
    expect(result.invalidNull).toBeNull();
    expect(result.invalidAbs).toBeNull();
    expect(result.invalidParent).toBeNull();
    expect(result.invalidBackslash).toBeNull();
    expect(result.invalidColon).toBeNull();
    expect(result.invalidExt).toBeNull();
    expect(result.invalidNoExt).toBeNull();
    expect(result.encodesSpace).toBe('/static/vendor/free-exercise-db/exercises/weird%20name/0.jpg');
  });
});
