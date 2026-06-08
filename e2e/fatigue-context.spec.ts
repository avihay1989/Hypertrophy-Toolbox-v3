/**
 * E2E Test: Advisory Fatigue Context (Phase 2D-A)
 *
 * Covers the two UI surfaces:
 * - Profile settings: an independent fatigue-context toggle (separate from
 *   Learned Calibration), persisted via the real backend.
 * - Workout Controls: a neutral "Fatigue context" chip + an advisory section
 *   rendered INSIDE "show the math", below the strength evidence. The estimate
 *   is mocked so the additive `fatigue_context` block is deterministic.
 *
 * Guardrails asserted: the advisory layer never changes the suggested
 * weight/reps inputs, always carries "This does not change your suggestion.",
 * and is hidden entirely when the estimate omits the block. See
 * docs/user_profile/LEARNED_CALIBRATION_PLAN.md §"Phase 2D-A".
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';
import type { Page } from '@playwright/test';

const FATIGUE_CONTEXT_SETTINGS = '/api/user_profile/fatigue_context_settings';
const CALIBRATION_SETTINGS = '/api/user_profile/calibration_settings';
const ESTIMATE = '/api/user_profile/estimate';

// Settings persist in the shared DB — force the toggle back off around each test.
test.beforeEach(async ({ page }) => {
  await page.request.post(FATIGUE_CONTEXT_SETTINGS, { data: { enabled: false } });
});
test.afterEach(async ({ page }) => {
  await page.request.post(FATIGUE_CONTEXT_SETTINGS, { data: { enabled: false } });
});

function estimateWithFatigue(fatigueContext: unknown) {
  return {
    ok: true,
    status: 'success',
    data: {
      weight: 60,
      sets: 3,
      min_rep: 6,
      max_rep: 8,
      rir: 3,
      rpe: 7,
      source: 'profile',
      reason: 'profile',
      is_dumbbell: false,
      trace: {
        source: 'profile',
        steps: [{ label: 'Reference lift', value: '60 kg × 8', detail: 'Direct match' }],
      },
      ...(fatigueContext ? { fatigue_context: fatigueContext } : {}),
    },
  };
}

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

test.describe('Fatigue Context — Profile settings', () => {
  test('enables independently of learned calibration', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);

    const section = page.locator('.profile-fatigue-context');
    await expect(section).toBeVisible();
    await expect(section).toContainText('Fatigue Context');

    const enabled = section.locator('input[name="fatigue_context_enabled"]');
    const source = section.locator('select[name="fatigue_context_source"]');
    const period = section.locator('select[name="fatigue_context_period"]');
    await expect(enabled).not.toBeChecked();
    await expect(source).toBeDisabled();
    await expect(period).toBeDisabled();

    // Enable — the lens selects unlock and the status text flips on.
    const enableResp = page.waitForResponse(
      (r) => r.url().includes(FATIGUE_CONTEXT_SETTINGS) && r.request().method() === 'POST',
    );
    await enabled.check();
    await enableResp;
    await expect(source).toBeEnabled();
    await expect(period).toBeEnabled();
    await expect(section.locator('[data-fatigue-context-text]')).toContainText('On');
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Fatigue context enabled');

    // The Learned Calibration toggle is untouched — the two are independent.
    await expect(
      page.locator('.profile-calibration input[name="calibration_mode"][value="off"]'),
    ).toBeChecked();

    consoleErrors.assertNoErrors();
  });

  test('persists the selected lens across reload', async ({ page }) => {
    await page.request.post(FATIGUE_CONTEXT_SETTINGS, {
      data: { enabled: true, context_source: 'logged', context_period: 'last_4_weeks' },
    });
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);

    const section = page.locator('.profile-fatigue-context');
    await expect(section.locator('input[name="fatigue_context_enabled"]')).toBeChecked();
    await expect(section.locator('select[name="fatigue_context_source"]')).toHaveValue('logged');
    await expect(section.locator('select[name="fatigue_context_period"]')).toHaveValue('last_4_weeks');
  });
});

test.describe('Fatigue Context — Workout Controls', () => {
  test('shows chip + advisory below the strength math, leaving inputs unchanged', async ({
    page,
    consoleErrors,
  }) => {
    consoleErrors.startCollecting();
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          estimateWithFatigue({
            enabled: true,
            muscle: 'Chest',
            muscle_label: 'Chest',
            has_landmarks: true,
            source: 'both',
            period: 'this_week',
            period_label: 'This week (Mon–Sun)',
            planned: { band: 'moderate', percent_of_mrv: 60, has_landmarks: true },
            logged: { band: 'light', percent_of_mrv: 30, has_landmarks: true },
            disagree: true,
            is_advisory_fallback: false,
            headline: 'Chest fatigue: moderate (planned) · light (logged).',
            advisory: 'This does not change your suggestion.',
          }),
        ),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    // Neutral chip is visible next to the provenance line.
    const chip = page.locator('#workout-estimate-fatigue-chip');
    await expect(chip).toBeVisible();
    await expect(chip).toContainText('Fatigue context');

    // Open "show the math".
    const toggle = page.locator('#workout-estimate-trace-toggle');
    const container = page.locator('#workout-estimate-trace');
    await toggle.click();
    await expect(container).toBeVisible();

    // The fatigue section renders below the strength steps, shows both bands
    // (they disagree), and carries the mandatory advisory line.
    const fatigue = container.locator('[data-fatigue-context]');
    await expect(fatigue).toBeVisible();
    await expect(fatigue).toContainText('Fatigue context');
    await expect(fatigue).toContainText('(planned)');
    await expect(fatigue).toContainText('(logged)');
    await expect(fatigue).toContainText('This does not change your suggestion.');

    // The advisory layer never touches the suggested inputs.
    await expect(page.locator('#weight')).toHaveValue('60');
    await expect(page.locator('#min_rep')).toHaveValue('6');
    await expect(page.locator('#max_rep_range')).toHaveValue('8');

    consoleErrors.assertNoErrors();
  });

  test('renders neutral advisory copy for an unranked muscle', async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          estimateWithFatigue({
            enabled: true,
            muscle: 'Neck',
            muscle_label: 'Neck',
            has_landmarks: false,
            source: 'both',
            period: 'this_week',
            period_label: 'This week (Mon–Sun)',
            planned: null,
            logged: null,
            disagree: false,
            is_advisory_fallback: true,
            headline: "Fatigue context isn't ranked for Neck yet.",
            advisory: 'This does not change your suggestion.',
          }),
        ),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    await page.locator('#workout-estimate-trace-toggle').click();
    const fatigue = page.locator('#workout-estimate-trace [data-fatigue-context]');
    await expect(fatigue).toContainText("isn't ranked");
    await expect(fatigue).toContainText('This does not change your suggestion.');

    consoleErrors.assertNoErrors();
  });

  test('hides chip and section when the estimate omits fatigue context', async ({
    page,
    consoleErrors,
  }) => {
    consoleErrors.startCollecting();
    await page.route(`**${ESTIMATE}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(estimateWithFatigue(null)),
      });
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectFirstExercise(page);

    await expect(page.locator('#workout-estimate-fatigue-chip')).toBeHidden();
    await page.locator('#workout-estimate-trace-toggle').click();
    await expect(page.locator('#workout-estimate-trace')).toBeVisible();
    await expect(
      page.locator('#workout-estimate-trace [data-fatigue-context]'),
    ).toHaveCount(0);

    consoleErrors.assertNoErrors();
  });
});
