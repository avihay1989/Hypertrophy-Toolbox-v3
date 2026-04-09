/**
 * E2E Test: Browser Navigation State (Stateless Mode)
 *
 * Contract:
 * - Routine cascade always resets on back/refresh.
 * - Deep-link query for routine is ignored.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';

type RoutineState = {
  env: string;
  program: string;
  day: string;
  hidden: string;
};

async function readRoutineState(page): Promise<RoutineState> {
  const env = await page.locator(SELECTORS.ROUTINE_ENV).inputValue();
  const program = await page.locator(SELECTORS.ROUTINE_PROGRAM).inputValue();
  const day = await page.locator(SELECTORS.ROUTINE_DAY).inputValue();
  const hidden = await page.locator('#routine').inputValue();
  return { env, program, day, hidden };
}

async function selectRoutine(page): Promise<void> {
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

function expectBlankState(state: RoutineState): void {
  expect(state.env).toBe('');
  expect(state.program).toBe('');
  expect(state.day).toBe('');
  expect(state.hidden).toBe('');
}

test.describe('Browser Navigation Stateless Behavior', () => {
  test('back navigation resets full routine selection', async ({ page }) => {
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);

    await page.goto(ROUTES.WORKOUT_LOG);
    await waitForPageReady(page);
    await page.goBack();
    await waitForPageReady(page);

    const state = await readRoutineState(page);
    expectBlankState(state);
  });

  test('page refresh resets full routine selection', async ({ page }) => {
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await selectRoutine(page);

    await page.reload();
    await waitForPageReady(page);

    const state = await readRoutineState(page);
    expectBlankState(state);
  });

  test('deep-link routine query is ignored in stateless mode', async ({ page }) => {
    await page.goto('/workout_plan?routine=GYM%20-%20Full%20Body%20-%20Workout%20A');
    await waitForPageReady(page);

    const state = await readRoutineState(page);
    expectBlankState(state);
  });
});
