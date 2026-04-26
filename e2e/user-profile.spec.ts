import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

test.beforeEach(async ({ page }) => {
  await resetWorkoutPlan(page);
  await page.request.post('/api/user_profile', {
    data: {
      gender: null,
      age: null,
      height_cm: null,
      weight_kg: null,
      experience_years: null,
    },
  });
  await page.request.post('/api/user_profile/lifts', {
    data: [
      { lift_key: 'barbell_bicep_curl', weight_kg: null, reps: null },
      { lift_key: 'barbell_bench_press', weight_kg: null, reps: null },
    ],
  });
  await page.request.post('/api/user_profile/preferences', {
    data: { complex: 'heavy', accessory: 'moderate', isolated: 'light' },
  });
});

test.describe('User Profile', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('profile page saves each section without reloading', async ({ page }) => {
    await expect(page.locator(SELECTORS.PAGE_USER_PROFILE)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_USER_PROFILE)).toBeVisible();

    await page.locator('#profile-gender').selectOption('Other');
    await page.locator('#profile-age').fill('30');
    await page.locator('#profile-height').fill('180');
    await page.locator('#profile-weight').fill('80');
    await page.locator('#profile-experience').fill('5');
    await page.locator('#profile-demographics-form button[type="submit"]').click();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Profile saved');

    const benchRow = page.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    await benchRow.locator('[name="weight_kg"]').fill('100');
    await benchRow.locator('[name="reps"]').fill('5');
    await page.locator('#profile-lifts-form button[type="submit"]').click();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Reference lifts saved');

    await page.locator('label.segmented-option:has(input[name="complex"][value="moderate"])').click();
    await page.locator('#profile-preferences-form button[type="submit"]').click();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Preferences saved');

    await page.reload();
    await waitForPageReady(page);
    await expect(page.locator('#profile-age')).toHaveValue('30');
    await expect(benchRow.locator('[name="weight_kg"]')).toHaveValue('100.0');
    await expect(page.locator('input[name="complex"][value="moderate"]')).toBeChecked();
  });

  test('workout plan applies profile estimate and preserves it after add', async ({ page }) => {
    await page.request.post('/api/user_profile/lifts', {
      data: [{ lift_key: 'barbell_bicep_curl', weight_kg: 35, reps: 8 }],
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
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

    let estimateRequests = 0;
    page.on('request', request => {
      if (request.url().includes('/api/user_profile/estimate')) {
        estimateRequests += 1;
      }
    });

    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('EZ Bar Preacher Curl');

    await expect(page.locator('#weight')).toHaveValue('11.25');
    await expect(page.locator('#sets')).toHaveValue('3');
    await expect(page.locator('#min_rep')).toHaveValue('10');
    await expect(page.locator('#max_rep_range')).toHaveValue('15');
    await expect(page.locator('#rir')).toHaveValue('2');
    await expect(page.locator('#rpe')).toHaveValue('7.5');
    await expect(page.locator('#workout-estimate-provenance')).toHaveText('from your profile');
    expect(estimateRequests).toBe(1);

    const postAddEstimate = page.waitForResponse(response =>
      response.url().includes('/api/user_profile/estimate') && response.status() === 200
    );
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await postAddEstimate;
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText(/added|already/i);

    await expect(page.locator('#weight')).toHaveValue('11.25');
    await expect(page.locator('#sets')).toHaveValue('3');
    await expect(page.locator('#min_rep')).toHaveValue('10');
    await expect(page.locator('#max_rep_range')).toHaveValue('15');
    await expect(page.locator('#rir')).toHaveValue('2');
    await expect(page.locator('#rpe')).toHaveValue('7.5');
    await expect(page.locator('#workout-estimate-provenance')).toHaveText('from your profile');
  });
});
