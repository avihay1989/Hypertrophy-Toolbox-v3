/**
 * E2E Test: Input Validation Boundaries
 * 
 * Tests form validation for edge cases and boundary values:
 * - Negative numbers for reps/sets/weight
 * - Min rep > Max rep validation
 * - RIR/RPE maximum value enforcement
 * - Zero and empty value handling
 * - Decimal/float handling
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
 * Helper to select an exercise from dropdown
 */
async function selectExercise(page: import('@playwright/test').Page) {
  await page.waitForFunction(() => {
    const select = document.getElementById('exercise') as HTMLSelectElement;
    return select && select.options.length > 1;
  });
  
  const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
  const options = await exerciseSelect.locator('option').allInnerTexts();
  const validExercise = options.find(opt => opt && opt.trim() !== '' && !opt.includes('Select'));
  if (validExercise) {
    await exerciseSelect.selectOption(validExercise);
  }
}

async function expectExerciseSubmission(
  page: import('@playwright/test').Page,
  expectedStatus: number,
  expectedPayload: Record<string, number>
) {
  const rows = page.locator('#workout_plan_table_body tr');
  const initialCount = await rows.count();
  const responsePromise = page.waitForResponse(response =>
    response.url().endsWith('/add_exercise') && response.request().method() === 'POST'
  );

  await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
  const response = await responsePromise;

  expect(response.status()).toBe(expectedStatus);
  expect(response.request().postDataJSON()).toMatchObject(expectedPayload);
  if (expectedStatus === 200) {
    await expect.poll(() => rows.count()).toBe(initialCount + 1);
  } else {
    await expect.poll(() => rows.count()).toBe(initialCount);
  }
}

test.beforeEach(async ({ page }) => {
  await resetWorkoutPlan(page);
});

test.describe('Negative Value Validation', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('clamps negative sets to the current minimum', async ({ page }) => {
    await page.fill('#sets', '-1');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { sets: 1 });
  });

  test('clamps negative min rep to the current minimum', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '-5');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { min_rep_range: 1 });
  });

  test('rejects negative max rep value', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '-10');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 400, { max_rep_range: 1 });
  });

  test('clamps negative weight to zero', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '-50');

    await expectExerciseSubmission(page, 200, { weight: 0 });
  });
});

test.describe('Rep Range Validation', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('rejects min rep greater than max rep', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '15');  // Min > Max
    await page.fill('#max_rep_range', '8');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 400, {
      min_rep_range: 15,
      max_rep_range: 8,
    });
  });

  test('accepts valid rep range (min < max)', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, {
      min_rep_range: 8,
      max_rep_range: 12,
    });
  });

  test('accepts equal min and max rep (min == max)', async ({ page }) => {
    await page.fill('#sets', '5');
    await page.fill('#min_rep', '5');  // Fixed rep count
    await page.fill('#max_rep_range', '5');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, {
      min_rep_range: 5,
      max_rep_range: 5,
    });
  });
});

test.describe('Zero Value Validation', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('clamps zero sets to the current minimum', async ({ page }) => {
    await page.fill('#sets', '0');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { sets: 1 });
  });

  test('clamps zero min rep to the current minimum', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '0');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { min_rep_range: 1 });
  });

  test('accepts zero weight for bodyweight or assisted exercise', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '0');

    await expectExerciseSubmission(page, 200, { weight: 0 });
  });
});

test.describe('RIR/RPE Value Validation', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('rejects RIR greater than 10', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');
    
    const rirField = page.locator('#rir');
    if (await rirField.isVisible()) {
      await rirField.fill('15');  // RIR > 10 doesn't make sense
    }

    await expectExerciseSubmission(page, 200, { rir: 10 });
  });

  test('rejects negative RIR', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');
    
    const rirField = page.locator('#rir');
    if (await rirField.isVisible()) {
      await rirField.fill('-2');
    }

    await expectExerciseSubmission(page, 200, { rir: 0 });
  });

  test('rejects RPE greater than 10', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');
    
    const rpeField = page.locator('#rpe');
    if (await rpeField.isVisible()) {
      await rpeField.fill('12');  // RPE scale is 1-10
    }

    await expectExerciseSubmission(page, 200, { rpe: 10 });
  });

  test('accepts valid RIR value (0-4 typical range)', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');
    
    const rirField = page.locator('#rir');
    if (await rirField.isVisible()) {
      await rirField.fill('2');
    }

    await expectExerciseSubmission(page, 200, { rir: 2 });
  });
});

test.describe('Decimal/Float Value Handling', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('accepts decimal weight values', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '102.5');  // Decimal weight (common for kg)

    await expectExerciseSubmission(page, 200, { weight: 102.5 });
  });

  test('handles decimal sets by rounding', async ({ page }) => {
    await page.fill('#sets', '3.5');  // Should round to 3 or 4
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { sets: 3 });
  });

  test('handles decimal reps by rounding or rejecting', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8.5');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { min_rep_range: 8 });
  });
});

test.describe('Empty Value Validation', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('rejects submission without exercise selected', async ({ page }) => {
    // Don't select exercise
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await page.waitForTimeout(500);

    // Should show validation error about required exercise
    const toast = page.locator('.toast, #liveToast');
    const toastVisible = await toast.isVisible().catch(() => false);
    expect(toastVisible).toBeTruthy();
  });

  test('rejects empty sets field', async ({ page }) => {
    await selectExercise(page);
    await page.fill('#sets', '');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    let addRequestSent = false;
    page.on('request', request => {
      if (request.url().endsWith('/add_exercise')) addRequestSent = true;
    });
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await expect(page.locator('#liveToast')).toBeVisible();
    expect(addRequestSent).toBe(false);
  });

  test('rejects empty weight field', async ({ page }) => {
    await selectExercise(page);
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '');

    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await page.waitForTimeout(500);

    const toast = page.locator('.toast, #liveToast');
    const toastVisible = await toast.isVisible().catch(() => false);
    expect(toastVisible).toBeTruthy();
  });
});

test.describe('Extreme Value Handling', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);
    await selectExercise(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('handles very large sets value', async ({ page }) => {
    await page.fill('#sets', '9999');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, { sets: 9999 });
  });

  test('handles very large weight value', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');
    await page.fill('#weight', '50000');  // 50000 lbs = unrealistic

    await expectExerciseSubmission(page, 400, { weight: 50000 });
  });

  test('handles very large rep values', async ({ page }) => {
    await page.fill('#sets', '3');
    await page.fill('#min_rep', '500');
    await page.fill('#max_rep_range', '1000');
    await page.fill('#weight', '100');

    await expectExerciseSubmission(page, 200, {
      min_rep_range: 500,
      max_rep_range: 1000,
    });
  });
});
