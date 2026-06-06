/**
 * E2E Test: Learned Calibration (MVP)
 *
 * Covers the UI surfaces added for learned strength calibration:
 * - Profile settings toggle (off/suggest) with persistence + toast (real backend).
 * - Workout Controls learned-source badge, "show the math" details, and the
 *   Apply / Keep / Reset-per-exercise affordances (estimate mocked so the flow
 *   is deterministic without seeding a scored-log history in the shared DB).
 *
 * Guardrails: Apply only populates the inputs (never persists); Reset clears the
 * row and falls back to the prior estimate chain. See
 * docs/user_profile/LEARNED_CALIBRATION_PLAN.md.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';
import type { Page } from '@playwright/test';

const CALIBRATION_SETTINGS = '/api/user_profile/calibration_settings';
const CALIBRATION_DASHBOARD = '/api/user_profile/calibration/dashboard';
const CALIBRATION_PROMOTE = '/api/user_profile/calibration/promote';
const CALIBRATION_RESET = '/api/user_profile/calibration/reset';
const CALIBRATION_IGNORE = '/api/user_profile/calibration/ignore_transfer';
const ESTIMATE = '/api/user_profile/estimate';

// Keep the shared DB clean: calibration mode is persistent, so force it back
// off around every test.
test.beforeEach(async ({ page }) => {
  await page.request.post(CALIBRATION_SETTINGS, {
    data: { mode: 'off', allow_related_exercise_learning: false },
  });
});
test.afterEach(async ({ page }) => {
  await page.request.post(CALIBRATION_SETTINGS, {
    data: { mode: 'off', allow_related_exercise_learning: false },
  });
});

test.describe('Learned Calibration — Profile settings', () => {
  test('enable then disable learned suggestions', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);

    const section = page.locator('.profile-calibration');
    await expect(section).toBeVisible();
    await expect(section).toContainText('Learned Calibration');

    const offRadio = section.locator('input[name="calibration_mode"][value="off"]');
    const suggestRadio = section.locator('input[name="calibration_mode"][value="suggest"]');
    const relatedCheckbox = section.locator('input[name="allow_related_exercise_learning"]');
    await expect(offRadio).toBeChecked();
    await expect(relatedCheckbox).toBeDisabled();

    // Enable — radios are visually hidden, so click the wrapping label.
    const enableResp = page.waitForResponse(
      (r) => r.url().includes(CALIBRATION_SETTINGS) && r.request().method() === 'POST',
    );
    await section.locator('.segmented-option', { hasText: 'Suggest' }).click();
    await enableResp;
    await expect(suggestRadio).toBeChecked();
    await expect(relatedCheckbox).toBeEnabled();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Learned suggestions enabled');
    await expect(section.locator('[data-calibration-text]')).toContainText('On');

    const relatedResp = page.waitForResponse(
      (r) => r.url().includes(CALIBRATION_SETTINGS) && r.request().method() === 'POST',
    );
    await relatedCheckbox.check();
    await relatedResp;
    await expect(relatedCheckbox).toBeChecked();
    await expect(section.locator('[data-calibration-text]')).toContainText('related learned');

    // Disable — back to off.
    const disableResp = page.waitForResponse(
      (r) => r.url().includes(CALIBRATION_SETTINGS) && r.request().method() === 'POST',
    );
    await section.locator('.segmented-option', { hasText: 'Off' }).click();
    await disableResp;
    await expect(offRadio).toBeChecked();
    await expect(relatedCheckbox).toBeDisabled();
    await expect(relatedCheckbox).not.toBeChecked();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('turned off');

    consoleErrors.assertNoErrors();
  });

  test('suggest mode persists across reload', async ({ page }) => {
    await page.request.post(CALIBRATION_SETTINGS, {
      data: { mode: 'suggest', allow_related_exercise_learning: true },
    });
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);
    await expect(
      page.locator('input[name="calibration_mode"][value="suggest"]'),
    ).toBeChecked();
    await expect(page.locator('input[name="allow_related_exercise_learning"]')).toBeChecked();
  });

  test('promotes a learned row to a Profile reference lift', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.route(`**${CALIBRATION_DASHBOARD}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            learned: [
              {
                exercise_name: 'Barbell Bench Press',
                confidence: 'medium',
                sample_count: 1,
                estimated_1rm: 126.67,
                suggested_weight: 102.5,
                suggested_min_reps: 6,
                suggested_max_reps: 8,
                last_observed_at: '2026-06-06 10:00:00',
                promotable: true,
                lift_key: 'barbell_bench_press',
                lift_label: 'Barbell Bench Press',
                existing_reference: null,
                promote_weight_kg: 100,
                promote_reps: 8,
              },
            ],
            ignored_transfers: [],
          },
        }),
      });
    });
    await page.route(`**${CALIBRATION_PROMOTE}`, async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        exercise: 'Barbell Bench Press',
        overwrite: false,
      });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            lift_key: 'barbell_bench_press',
            lift_label: 'Barbell Bench Press',
            weight_kg: 100,
            reps: 8,
            overwrote: false,
            previous: null,
          },
        }),
      });
    });

    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);

    const review = page.locator('[data-calibration-review]');
    await expect(review.locator('[data-learned-table]')).toBeVisible();
    await expect(review).toContainText('Barbell Bench Press');
    const button = review.locator('[data-promote-exercise="Barbell Bench Press"]');
    await expect(button).toBeVisible();

    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Save 100 kg × 8');
      expect(dialog.message()).toContain('declared Profile reference lift');
      await dialog.accept();
    });
    await button.click();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText(
      'Promoted to Profile reference lift: Barbell Bench Press 100 kg × 8',
    );

    consoleErrors.assertNoErrors();
  });

  test('promote overwrite confirm shows old and new reference values', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.route(`**${CALIBRATION_DASHBOARD}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            learned: [
              {
                exercise_name: 'Barbell Bench Press',
                confidence: 'medium',
                sample_count: 1,
                estimated_1rm: 126.67,
                suggested_weight: 102.5,
                suggested_min_reps: 6,
                suggested_max_reps: 8,
                last_observed_at: '2026-06-06 10:00:00',
                promotable: true,
                lift_key: 'barbell_bench_press',
                lift_label: 'Barbell Bench Press',
                existing_reference: { weight_kg: 90, reps: 5 },
                promote_weight_kg: 100,
                promote_reps: 8,
              },
            ],
            ignored_transfers: [],
          },
        }),
      });
    });
    await page.route(`**${CALIBRATION_PROMOTE}`, async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        exercise: 'Barbell Bench Press',
        overwrite: true,
      });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            lift_key: 'barbell_bench_press',
            lift_label: 'Barbell Bench Press',
            weight_kg: 100,
            reps: 8,
            overwrote: true,
            previous: { weight_kg: 90, reps: 5 },
          },
        }),
      });
    });

    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);

    const button = page.locator('[data-promote-exercise="Barbell Bench Press"]');
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Current: 90 kg × 5');
      expect(dialog.message()).toContain('New (from your logged set): 100 kg × 8');
      await dialog.accept();
    });
    await button.click();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText(
      'Promoted to Profile reference lift: Barbell Bench Press 100 kg × 8',
    );

    consoleErrors.assertNoErrors();
  });
});

test.describe('Learned Calibration — Workout Controls badge & actions', () => {
  const LEARNED_ESTIMATE = {
    ok: true,
    status: 'success',
    data: {
      weight: 142.5,
      sets: 3,
      min_rep: 6,
      max_rep: 8,
      rir: 2,
      rpe: 8,
      source: 'learned',
      reason: 'learned_calibration',
      is_dumbbell: false,
      trace: {
        source: 'learned',
        confidence: 'high',
        sample_count: 3,
        steps: [
          {
            label: 'Learned from your logged sets',
            value: '120 kg × 6–8',
            detail: 'Calibrated from 3 scored logs for this exact exercise (confidence: high).',
          },
          {
            label: 'Estimated strength',
            value: '~152 kg e1RM',
            detail: 'Canonical Epley estimate from your best recent top set.',
          },
        ],
      },
    },
  };

  const FALLBACK_ESTIMATE = {
    ok: true,
    status: 'success',
    data: {
      weight: 60,
      sets: 3,
      min_rep: 6,
      max_rep: 8,
      rir: 3,
      rpe: 7,
      source: 'log',
      is_dumbbell: false,
      trace: {
        source: 'log',
        steps: [{ label: 'From your last logged set', value: '60 kg × 6–8' }],
      },
    },
  };

  const RELATED_ESTIMATE = {
    ok: true,
    status: 'success',
    data: {
      weight: 35,
      sets: 3,
      min_rep: 8,
      max_rep: 10,
      rir: 2,
      rpe: 8,
      source: 'related_learned',
      reason: 'related_calibration',
      is_dumbbell: true,
      trace: {
        source: 'related_learned',
        confidence: 'high',
        sample_count: 4,
        source_exercise: 'Barbell Bench Press',
        target_exercise: 'Incline Dumbbell Bench Press',
        transfer_ratio: 0.72,
        load_basis: 'total_to_per_hand',
        steps: [
          {
            label: 'Related learned calibration',
            value: 'Learned from Barbell Bench Press',
            detail: '4 scored logs, confidence: high. Exact learned/log data for Incline Dumbbell Bench Press was not available.',
          },
          {
            label: 'Transfer',
            value: 'Barbell Bench Press -> Incline Dumbbell Bench Press',
            detail: 'Relationship: manual; ratio 0.72; load basis: total to per hand (factor 0.5).',
          },
        ],
      },
    },
  };

  async function selectFirstExercise(page: Page): Promise<void> {
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

    const estimateDone = page.waitForResponse((r) => r.url().includes(ESTIMATE));
    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('Barbell Bench Press');
    await estimateDone;
  }

  test('shows learned badge, details, Apply, and Reset fallback', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();

    // Mutable mock: learned until a reset clears it, then fall back.
    let learnedActive = true;
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(learnedActive ? LEARNED_ESTIMATE : FALLBACK_ESTIMATE),
      });
    });
    await page.route(`**${CALIBRATION_RESET}`, async (route) => {
      learnedActive = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, status: 'success', data: { exercise: 'Barbell Bench Press' } }),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    // Badge reflects the learned source + confidence.
    const badge = page.locator('#workout-estimate-learned-badge');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute('data-confidence', 'high');
    await expect(badge).toContainText('Learned');
    await expect(page.locator('#workout-estimate-provenance')).toContainText('learned');

    // Open the explanation details.
    const toggle = page.locator('#workout-estimate-trace-toggle');
    const container = page.locator('#workout-estimate-trace');
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(container).toBeVisible();
    await expect(container).toContainText('Learned from your recent logs');
    await expect(container).toContainText('Estimated strength');

    // Apply populates the Weight input (client-side only).
    const weightInput = page.locator('#weight');
    await page.locator('[data-learned-apply]').click();
    await expect(weightInput).toHaveValue('142.5');
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Suggestion applied');

    // Reset clears learned data and re-fetches → fallback, badge hidden.
    const resetDone = page.waitForResponse((r) => r.url().includes(CALIBRATION_RESET));
    const refetch = page.waitForResponse((r) => r.url().includes(ESTIMATE));
    await page.locator('[data-learned-reset]').click();
    await resetDone;
    await refetch;
    await expect(badge).toBeHidden();
    await expect(page.locator('#workout-estimate-provenance')).toContainText('from your last set');

    consoleErrors.assertNoErrors();
  });

  test('Keep current collapses details without changing the badge', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(LEARNED_ESTIMATE),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    const toggle = page.locator('#workout-estimate-trace-toggle');
    const container = page.locator('#workout-estimate-trace');
    await toggle.click();
    await expect(container).toBeVisible();

    await page.locator('[data-learned-keep]').click();
    await expect(container).toBeHidden();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    // Badge stays — Keep current does not dismiss the learned source.
    await expect(page.locator('#workout-estimate-learned-badge')).toBeVisible();

    consoleErrors.assertNoErrors();
  });

  test('shows related badge and Ignore source fallback', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();

    let relatedActive = true;
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(relatedActive ? RELATED_ESTIMATE : FALLBACK_ESTIMATE),
      });
    });
    await page.route(`**${CALIBRATION_IGNORE}`, async (route) => {
      relatedActive = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          status: 'success',
          data: {
            source_exercise: 'Barbell Bench Press',
            target_exercise: 'Incline Dumbbell Bench Press',
          },
        }),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    const badge = page.locator('#workout-estimate-learned-badge');
    await expect(badge).toBeVisible();
    await expect(badge).toContainText('Related');
    await expect(page.locator('#workout-estimate-provenance')).toContainText('related exercise');

    const toggle = page.locator('#workout-estimate-trace-toggle');
    const container = page.locator('#workout-estimate-trace');
    await toggle.click();
    await expect(container).toContainText('Learned from a related exercise');
    await expect(container).toContainText('Barbell Bench Press');
    await expect(page.locator('[data-related-ignore]')).toBeVisible();

    const ignoreDone = page.waitForResponse((r) => r.url().includes(CALIBRATION_IGNORE));
    const refetch = page.waitForResponse((r) => r.url().includes(ESTIMATE));
    await page.locator('[data-related-ignore]').click();
    await ignoreDone;
    await refetch;
    await expect(badge).toBeHidden();
    await expect(page.locator('#workout-estimate-provenance')).toContainText('from your last set');

    consoleErrors.assertNoErrors();
  });
});

test.describe('Learned Calibration — Golden Path (Real Data)', () => {
  // Test the full end-to-end loop without route mocks:
  // 1. Seed plan with an exercise
  // 2. Import into Workout Log
  // 3. Edit scored metrics to simulate an aggressive set
  // 4. Return to Workout Plan and verify the real Learned Estimate is shown
  test('end-to-end loop triggers auto-calibration on log save', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();

    // 1. Enable suggestion mode
    const settingsResponse = await page.request.post(CALIBRATION_SETTINGS, { data: { mode: 'suggest' } });
    expect(settingsResponse.ok()).toBeTruthy();

    // 2. Seed the workout plan with Barbell Bench Press
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    // Select the routine structure
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

    const estimateDoneSeed = page.waitForResponse((r) => r.url().includes(ESTIMATE));
    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('Barbell Bench Press');
    await estimateDoneSeed;

    // Add one plan row. A single recent valid scored log is enough for the
    // shipped MVP to reach usable medium confidence.
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await page.waitForSelector('#workout_plan_table_body tr');

    // 3. Go to Workout Log
    await page.goto(ROUTES.WORKOUT_LOG);
    await waitForPageReady(page);

    // Import the planned row, then use the UI to create the real scored log.
    const importResponse = page.waitForResponse((r) => r.url().includes('/export_to_workout_log') && r.request().method() === 'POST');
    await page.locator('#import-from-plan-btn').click();
    expect((await importResponse).ok()).toBeTruthy();

    // Wait for the row to be present
    await page.waitForSelector('.workout-log-table tbody tr');
    const row = page.locator('.workout-log-table tbody tr').first();

    // Weight
    const weightCell = row.locator('td[data-field="scored_weight"]');
    await weightCell.locator('.editable-text').click();
    await weightCell.locator('input').fill('140');
    await weightCell.locator('input').blur();

    // Min Reps
    const minRepsCell = row.locator('td[data-field="scored_min_reps"]');
    await minRepsCell.locator('.editable-text').click();
    await minRepsCell.locator('input').fill('6');
    await minRepsCell.locator('input').blur();

    // Max Reps
    const maxRepsCell = row.locator('td[data-field="scored_max_reps"]');
    await maxRepsCell.locator('.editable-text').click();
    await maxRepsCell.locator('input').fill('6');
    await maxRepsCell.locator('input').blur();

    // RIR
    const rirCell = row.locator('td[data-field="scored_rir"]');
    await rirCell.locator('.editable-text').click();
    await rirCell.locator('input').fill('2');

    const updateResponse = page.waitForResponse((r) => r.url().includes('/update_workout_log') && r.request().method() === 'POST');
    await rirCell.locator('input').blur();
    expect((await updateResponse).ok()).toBeTruthy();

    await page.waitForSelector(SELECTORS.TOAST_CONTAINER + ' .toast.show');
    await page.locator(SELECTORS.TOAST_CONTAINER).locator('.btn-close').first().click();

    // 5. Go back to Workout Plan and select the exercise to see the learned estimate
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

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

    const estimateDoneReal = page.waitForResponse((r) => r.url().includes(ESTIMATE));
    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('Barbell Bench Press');
    await estimateDoneReal;

    // 6. Verify real badge (no mocks)
    const badge = page.locator('#workout-estimate-learned-badge');
    await expect(badge).toBeVisible();
    await expect(badge).toContainText('Learned');
    await expect(badge).toContainText('medium');
    await expect(page.locator('#workout-estimate-provenance')).toContainText('learned');

    consoleErrors.assertNoErrors();
  });
});
