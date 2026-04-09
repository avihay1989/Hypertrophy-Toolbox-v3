/**
 * E2E Test: Replace Exercise Error Messaging
 *
 * Verifies user-facing toasts for known replace_exercise failure reasons.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, expectToast } from './fixtures';

const BASE_URL = 'http://127.0.0.1:5000';
const TEST_ROUTINE = 'GYM - Full Body - Workout A';
const REPLACE_BUTTON_SELECTOR = 'button[data-action="replace"], .replace-btn, .btn-swap, [title*="Replace"]';

function extractExerciseName(entry: unknown): string | null {
  if (typeof entry === 'string') {
    return entry.trim() || null;
  }
  if (!entry || typeof entry !== 'object') {
    return null;
  }
  const candidate = entry as Record<string, unknown>;
  const raw =
    candidate.exercise ??
    candidate.exercise_name ??
    candidate.name ??
    candidate.value;
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
}

function extractRoutineName(entry: unknown): string | null {
  if (!entry || typeof entry !== 'object') {
    return null;
  }
  const candidate = entry as Record<string, unknown>;
  const raw = candidate.routine;
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
}

function extractDataRows(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  const candidate = payload as Record<string, unknown>;
  return Array.isArray(candidate.data) ? candidate.data : [];
}

async function selectRoutine(page: import('@playwright/test').Page) {
  await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
  await page.waitForFunction(() => {
    const select = document.getElementById('routine-program') as HTMLSelectElement;
    return !!select && select.options.length > 1;
  });
  await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Full Body');
  await page.waitForFunction(() => {
    const select = document.getElementById('routine-day') as HTMLSelectElement;
    return !!select && select.options.length > 1;
  });
  await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Workout A');
}

async function ensureRoutineHasExercises(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext,
  minimumCount: number
) {
  await selectRoutine(page);

  const rowLocator = page.locator('#workout_plan_table_body tr');
  let currentCount = await rowLocator.count();
  if (currentCount >= minimumCount) {
    return;
  }

  const planResponse = await request.get(`${BASE_URL}/get_workout_plan`);
  const planPayload = await planResponse.json().catch(() => ({}));
  const routineRows = extractDataRows(planPayload).filter(
    (row) => extractRoutineName(row) === TEST_ROUTINE
  );
  const existingNames = new Set(
    routineRows.map(extractExerciseName).filter((name): name is string => Boolean(name))
  );
  currentCount = routineRows.length;

  const allResponse = await request.get(`${BASE_URL}/get_all_exercises`);
  const allPayload = await allResponse.json().catch(() => ({}));
  const allRows = extractDataRows(allPayload);

  const addCandidates = allRows
    .map(extractExerciseName)
    .filter((name): name is string => Boolean(name))
    .filter((name) => !existingNames.has(name));

  for (const exerciseName of addCandidates) {
    if (currentCount >= minimumCount) {
      break;
    }
    const addResponse = await request.post(`${BASE_URL}/add_exercise`, {
      data: {
        routine: TEST_ROUTINE,
        exercise: exerciseName,
        sets: 3,
        min_rep_range: 8,
        max_rep_range: 12,
        weight: 100,
        rir: 2,
      },
    });
    if (addResponse.ok()) {
      currentCount += 1;
      existingNames.add(exerciseName);
    }
  }

  await page.reload();
  await waitForPageReady(page);
  await selectRoutine(page);
}

async function getVisibleReplaceButton(page: import('@playwright/test').Page) {
  const replaceBtn = page.locator('#workout_plan_table_body tr').locator(REPLACE_BUTTON_SELECTOR).first();
  await expect(replaceBtn).toBeVisible({ timeout: 5000 });
  return replaceBtn;
}

function buildReplaceErrorPayload(reason: string, message: string) {
  return {
    ok: false,
    status: 'error',
    message,
    error: {
      code: reason.toUpperCase(),
      reason,
      message
    }
  };
}

test.describe('Replace Exercise Error Messaging', () => {
  test.beforeEach(async ({ page, request, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await ensureRoutineHasExercises(page, request, 1);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('shows warning when no alternative exists', async ({ page }) => {
    await page.route('**/replace_exercise', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          buildReplaceErrorPayload(
            'no_candidates',
            'No alternative exercises found for Chest with Barbell'
          )
        ),
      });
    });

    const replaceBtn = await getVisibleReplaceButton(page);
    const responsePromise = page.waitForResponse((res) =>
      res.url().includes('/replace_exercise') && res.request().method() === 'POST'
    );

    await replaceBtn.click();
    await responsePromise;

    await expectToast(page, /No alternative found for this muscle\/equipment/i);
    await expect(replaceBtn).toBeEnabled();
  });

  test('shows warning when all alternatives already exist in routine', async ({ page }) => {
    await page.route('**/replace_exercise', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          buildReplaceErrorPayload(
            'duplicate',
            'All candidate exercises are already in this routine'
          )
        ),
      });
    });

    const replaceBtn = await getVisibleReplaceButton(page);
    const responsePromise = page.waitForResponse((res) =>
      res.url().includes('/replace_exercise') && res.request().method() === 'POST'
    );

    await replaceBtn.click();
    await responsePromise;

    await expectToast(page, /All alternatives are already in this routine/i);
    await expect(replaceBtn).toBeEnabled();
  });

  test('shows warning when exercise metadata is missing', async ({ page }) => {
    await page.route('**/replace_exercise', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          buildReplaceErrorPayload(
            'missing_metadata',
            'Exercise is missing muscle group or equipment metadata'
          )
        ),
      });
    });

    const replaceBtn = await getVisibleReplaceButton(page);
    const responsePromise = page.waitForResponse((res) =>
      res.url().includes('/replace_exercise') && res.request().method() === 'POST'
    );

    await replaceBtn.click();
    await responsePromise;

    await expectToast(page, /missing muscle\/equipment data and cannot be replaced/i);
    await expect(replaceBtn).toBeEnabled();
  });
});
