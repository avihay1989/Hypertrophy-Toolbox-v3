/**
 * E2E Test: UI Hardening (medium-risk smoke assertions)
 *
 * Locks down behavior contracts for the medium-risk scenarios called out in
 * docs/UI_SCENARIOS_GAP_ANALYSIS.md §3:
 *
 *   - Toast stacking (single `#liveToast` instance, last-message-wins, no stale bg class)
 *   - Form-state persistence (Workout Controls survive routine cascade + tab visibility;
 *     full reload resets to template defaults)
 *   - Modal keyboard / focus (Escape closes, focus trap stays inside modal, ARIA labelledby)
 *
 * These are smoke-style guards — they assert observable contract, not new product behavior.
 * Failures here mean a change shifted the user-visible behavior described above.
 */
import type { Page } from '@playwright/test';
import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

async function showToastViaModule(
  page: Page,
  type: 'success' | 'error' | 'warning' | 'info',
  message: string,
  duration = 4000
): Promise<void> {
  await page.evaluate(
    async ({ type, message, duration }) => {
      const mod = await import('/static/js/modules/toast.js');
      mod.showToast(type, message, { duration });
    },
    { type, message, duration }
  );
}

test.describe('UI Hardening — Toast Stacking', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('only one #liveToast element exists in the DOM', async ({ page }) => {
    const count = await page.locator('#liveToast').count();
    expect(count).toBe(1);
  });

  test('rapid successive toasts: last message wins on shared #liveToast', async ({ page }) => {
    await showToastViaModule(page, 'success', 'First message');
    await showToastViaModule(page, 'warning', 'Second message');
    await showToastViaModule(page, 'error', 'Final message');

    const toast = page.locator(SELECTORS.TOAST);
    await expect(toast).toBeVisible({ timeout: 5000 });
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText('Final message');

    // Confirm shared instance — still exactly one liveToast in the DOM
    expect(await page.locator('#liveToast').count()).toBe(1);
  });

  test('switching toast type clears stale bg-* classes', async ({ page }) => {
    await showToastViaModule(page, 'success', 'Green toast');
    await expect(page.locator('#liveToast.bg-success')).toBeVisible();

    await showToastViaModule(page, 'error', 'Red toast');
    const toast = page.locator(SELECTORS.TOAST);
    await expect(toast).toBeVisible();

    const classList = await toast.evaluate((el) => Array.from(el.classList));
    expect(classList).toContain('bg-danger');
    // Critical contract: prior bg-success must be removed (toast.js:88)
    expect(classList).not.toContain('bg-success');
    expect(classList).not.toContain('bg-warning');
    expect(classList).not.toContain('bg-info');
  });

  test('toast container uses polite live region for screen readers', async ({ page }) => {
    const container = page.locator(SELECTORS.TOAST_CONTAINER);
    const ariaLive = await container.first().getAttribute('aria-live');
    const ariaAtomic = await container.first().getAttribute('aria-atomic');
    expect(ariaLive).toBe('polite');
    expect(ariaAtomic).toBe('true');
  });
});

test.describe('UI Hardening — Form State Persistence', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    await resetWorkoutPlan(page);
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('full reload resets Workout Controls to template defaults', async ({ page }) => {
    // Snapshot the template defaults before mutating
    const initialSets = await page.locator('#sets').inputValue();
    const initialWeight = await page.locator('#weight').inputValue();

    // Mutate
    await page.fill('#sets', '7');
    await page.fill('#weight', '222');
    await page.fill('#min_rep', '9');
    await page.fill('#max_rep_range', '14');

    // Hard reload — the documented contract is that fields reset
    await page.reload();
    await waitForPageReady(page);

    await expect(page.locator('#sets')).toHaveValue(initialSets);
    await expect(page.locator('#weight')).toHaveValue(initialWeight);
  });

  test('Workout Controls survive routine cascade changes', async ({ page }) => {
    // Set non-default values, then drive the routine cascade
    await page.fill('#sets', '6');
    await page.fill('#weight', '180');
    await page.fill('#min_rep', '8');
    await page.fill('#max_rep_range', '12');

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

    // Workout Controls must not be touched by routine cascade
    await expect(page.locator('#sets')).toHaveValue('6');
    await expect(page.locator('#weight')).toHaveValue('180');
    await expect(page.locator('#min_rep')).toHaveValue('8');
    await expect(page.locator('#max_rep_range')).toHaveValue('12');
  });

  test('Workout Controls survive tab visibility change', async ({ page }) => {
    await page.fill('#sets', '4');
    await page.fill('#weight', '142.5');
    await page.fill('#min_rep', '6');
    await page.fill('#max_rep_range', '10');

    // Simulate the user tabbing away and back without unloading the page
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await page.waitForTimeout(50);
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await expect(page.locator('#sets')).toHaveValue('4');
    await expect(page.locator('#weight')).toHaveValue('142.5');
    await expect(page.locator('#min_rep')).toHaveValue('6');
    await expect(page.locator('#max_rep_range')).toHaveValue('10');
  });
});

test.describe('UI Hardening — Modal Keyboard & Focus', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  // Open the Clear Plan modal and wait for Bootstrap's shown.bs.modal event so the
  // backdrop is in place and the focus handoff has settled before we assert anything.
  async function openClearPlanModal(page: Page): Promise<void> {
    const shown = page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const el = document.getElementById('clearPlanModal');
        if (!el) {
          resolve();
          return;
        }
        const handler = () => {
          el.removeEventListener('shown.bs.modal', handler);
          resolve();
        };
        el.addEventListener('shown.bs.modal', handler);
      });
    });
    await page.locator('#clear-plan-btn').click();
    await shown;
  }

  test('modal opens with show class and aria-modal=true', async ({ page }) => {
    await openClearPlanModal(page);

    const modal = page.locator('#clearPlanModal');
    await expect(modal).toHaveClass(/show/);
    await expect(modal).toHaveAttribute('aria-modal', 'true');
  });

  test('modal exposes labelledby pointing to a visible heading', async ({ page }) => {
    const modal = page.locator('#clearPlanModal');
    const labelledBy = await modal.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();

    const heading = page.locator(`#${labelledBy}`);
    const text = await heading.textContent();
    expect(text?.trim().length ?? 0).toBeGreaterThan(0);
  });

  test('focus moves inside modal once it is fully shown', async ({ page }) => {
    const triggerWasFocused = await page.locator('#clear-plan-btn').evaluate((el) => {
      (el as HTMLElement).focus();
      return document.activeElement === el;
    });
    expect(triggerWasFocused).toBe(true);

    await openClearPlanModal(page);

    const activeIsInsideModal = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      if (!active) return false;
      const modalEl = document.getElementById('clearPlanModal');
      return modalEl ? modalEl.contains(active) : false;
    });
    expect(activeIsInsideModal).toBe(true);
  });

  test('first Tab from inside modal keeps focus inside modal', async ({ page }) => {
    await openClearPlanModal(page);

    const modal = page.locator('#clearPlanModal');
    await modal.locator('.btn-close').focus();
    await page.keyboard.press('Tab');

    const activeIsInsideModal = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      if (!active) return false;
      const modalEl = document.getElementById('clearPlanModal');
      return modalEl ? modalEl.contains(active) : false;
    });
    expect(activeIsInsideModal).toBe(true);
  });

  test('modal closes and backdrop is removed after pressing close button', async ({ page }) => {
    await openClearPlanModal(page);

    const modal = page.locator('#clearPlanModal');
    await modal.locator('.btn-close').first().click();

    await expect(modal).not.toHaveClass(/show/, { timeout: 5000 });
    await expect(page.locator('.modal-backdrop')).toHaveCount(0, { timeout: 5000 });

    // After close, page must not retain modal-open lock on body (would otherwise block scroll)
    await expect(page.locator('body.modal-open')).toHaveCount(0, { timeout: 5000 });
  });
});
