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
const CALIBRATION_RESET = '/api/user_profile/calibration/reset';
const ESTIMATE = '/api/user_profile/estimate';

// Keep the shared DB clean: calibration mode is persistent, so force it back
// off around every test.
test.beforeEach(async ({ page }) => {
  await page.request.post(CALIBRATION_SETTINGS, { data: { mode: 'off' } });
});
test.afterEach(async ({ page }) => {
  await page.request.post(CALIBRATION_SETTINGS, { data: { mode: 'off' } });
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
    await expect(offRadio).toBeChecked();

    // Enable — radios are visually hidden, so click the wrapping label.
    const enableResp = page.waitForResponse(
      (r) => r.url().includes(CALIBRATION_SETTINGS) && r.request().method() === 'POST',
    );
    await section.locator('.segmented-option', { hasText: 'Suggest' }).click();
    await enableResp;
    await expect(suggestRadio).toBeChecked();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Learned suggestions enabled');
    await expect(section.locator('[data-calibration-text]')).toContainText('On');

    // Disable — back to off.
    const disableResp = page.waitForResponse(
      (r) => r.url().includes(CALIBRATION_SETTINGS) && r.request().method() === 'POST',
    );
    await section.locator('.segmented-option', { hasText: 'Off' }).click();
    await disableResp;
    await expect(offRadio).toBeChecked();
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('turned off');

    consoleErrors.assertNoErrors();
  });

  test('suggest mode persists across reload', async ({ page }) => {
    await page.request.post(CALIBRATION_SETTINGS, { data: { mode: 'suggest' } });
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);
    await expect(
      page.locator('input[name="calibration_mode"][value="suggest"]'),
    ).toBeChecked();
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
            detail: 'Calibrated from 3 recent scored logs for this exact exercise (confidence: high).',
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
});
