/**
 * E2E Test: UI Hardening (medium-risk smoke assertions)
 *
 * Locks down behavior contracts for the medium-risk scenarios called out in
 * docs/UI_SCENARIOS_GAP_ANALYSIS.md §3:
 *
 *   - Toast stacking (single `#liveToast` instance, last-message-wins, no stale bg class)
 *   - Form-state persistence (Workout Controls survive routine cascade + tab visibility;
 *     full reload RESTORES the six controls from tab-scoped sessionStorage — KI-005)
 *   - Modal keyboard / focus (Escape closes, focus trap stays inside modal, ARIA labelledby)
 *
 * CONTRACT FLIP (KI-005, criterion 10): the previous contract — "full reload resets Workout
 * Controls to template defaults" — is deliberately INVERTED. Per the approved acceptance
 * criteria in docs/ki005_controls_persistence/PLANNING.md §0, a reload within the same tab
 * now RESTORES weight/sets/RIR/RPE/min-rep/max-rep. See the KI-005 describe block below.
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

/* ------------------------------------------------------------------------- *
 * KI-005 — Workout Controls persistence helpers
 *
 * Derived from the approved acceptance criteria in
 * docs/ki005_controls_persistence/PLANNING.md §0 + the four Gate 1 rulings
 * (AR-3, AR-4, TS-7, OWNER-1), plus the owner's 2026-07-13 rulings pinning the storage
 * contract and resolving criterion 3 to Reading A.
 * ------------------------------------------------------------------------- */

/**
 * PINNED storage contract (owner ruling, 2026-07-13): ONE JSON record under this single
 * namespaced, versioned sessionStorage key. Not six separate keys; not an unversioned name.
 */
const STORAGE_KEY = 'hypertrophy_workout_controls_v1';

/** The six Workout Controls (criterion 2 — exactly these, no others). */
type Controls = {
  weight: string;
  sets: string;
  rir: string;
  rpe: string;
  min_rep: string;
  max_rep_range: string;
};

/** DOM ids for the six controls (per PLANNING.md Plan v2 artifact table). */
const CONTROL_IDS: Record<keyof Controls, string> = {
  weight: '#weight',
  sets: '#sets',
  rir: '#rir',
  rpe: '#rpe',
  min_rep: '#min_rep',
  max_rep_range: '#max_rep_range',
};

/**
 * The PINNED template defaults (TS-7 owner ruling, Gate 1 2026-07-12):
 * weight 25 / sets 3 / RIR 3 / RPE 7 / min-rep 6 / max-rep 8.
 * Criterion 9's fallback target is these — NOT a per-exercise recommendation.
 */
const PINNED_DEFAULTS: Controls = {
  weight: '25',
  sets: '3',
  rir: '3',
  rpe: '7',
  min_rep: '6',
  max_rep_range: '8',
};

/** Distinctive values, all different from PINNED_DEFAULTS and inside the input min/max ranges. */
const NON_DEFAULT_CONTROLS: Controls = {
  weight: '137.5',
  sets: '5',
  rir: '1',
  rpe: '9',
  min_rep: '10',
  max_rep_range: '15',
};

/** Substring that must appear in whatever record the persistence layer writes. */
const CONTROLS_SENTINEL = NON_DEFAULT_CONTROLS.weight;

async function setAllControls(page: Page, values: Controls): Promise<void> {
  // min before max so any commit-time clamping sees a coherent range
  await page.fill(CONTROL_IDS.min_rep, values.min_rep);
  await page.fill(CONTROL_IDS.max_rep_range, values.max_rep_range);
  await page.fill(CONTROL_IDS.sets, values.sets);
  await page.fill(CONTROL_IDS.rir, values.rir);
  await page.fill(CONTROL_IDS.rpe, values.rpe);
  await page.fill(CONTROL_IDS.weight, values.weight);
}

async function readAllControls(page: Page): Promise<Controls> {
  const entries = await Promise.all(
    (Object.keys(CONTROL_IDS) as (keyof Controls)[]).map(
      async (field) => [field, await page.locator(CONTROL_IDS[field]).inputValue()] as const
    )
  );
  return Object.fromEntries(entries) as Controls;
}

async function expectControls(page: Page, expected: Controls): Promise<void> {
  for (const field of Object.keys(CONTROL_IDS) as (keyof Controls)[]) {
    await expect(page.locator(CONTROL_IDS[field]), `control ${field}`).toHaveValue(expected[field]);
  }
}

type StorageSnapshot = Record<string, string>;

async function readStorage(page: Page, which: 'session' | 'local'): Promise<StorageSnapshot> {
  return page.evaluate((w) => {
    const store = w === 'session' ? window.sessionStorage : window.localStorage;
    const out: Record<string, string> = {};
    for (let i = 0; i < store.length; i++) {
      const k = store.key(i);
      if (k !== null) out[k] = store.getItem(k) ?? '';
    }
    return out;
  }, which);
}

/**
 * Read the ONE pinned sessionStorage record and assert it carries the just-entered values.
 *
 * This assertion is what makes the criterion-9 / criterion-4 cases NON-VACUOUS: without a
 * KI-005 implementation no such record exists, so those tests fail here rather than
 * accidentally passing because "no persistence" looks like "fell back to defaults".
 */
async function readControlsRecord(page: Page): Promise<string> {
  const snapshot = await readStorage(page, 'session');
  const raw = snapshot[STORAGE_KEY];

  expect(
    raw,
    `expected the Workout Controls to be persisted as one JSON record under the pinned key ` +
      `"${STORAGE_KEY}" (criteria 1 + 6). sessionStorage: ${JSON.stringify(snapshot)}`
  ).toBeTruthy();
  expect(
    raw,
    `the record under "${STORAGE_KEY}" must carry the entered values (sentinel "${CONTROLS_SENTINEL}")`
  ).toContain(CONTROLS_SENTINEL);

  return raw;
}

/**
 * Overwrite the pinned record with an invalid payload (criterion 9).
 *
 * OWNER-5 RULING (2026-07-13) — "out of range" is defined by the inputs' DECLARED min/max
 * attributes ONLY; the module-invented caps are dropped. The declared bounds are:
 *   #weight  min 0, no max      #sets          min 1, no max
 *   #rir     min 0, MAX 10      #rpe           min 1, MAX 10
 *   #min_rep min 1, no max      #max_rep_range min 1, no max
 * Hence the two out-of-range shapes below:
 *   'above-max' — 999999 exceeds a declared `max` on #rir/#rpe ONLY. The four fields that
 *                 declare no `max` are NOT out of range and restore as stored (the owner's
 *                 verbatim accepted trade-off: "identical to typing 999999 without reloading,
 *                 and the server still rejects it at add time").
 *   'below-min' — -1 violates the declared `min` of ALL SIX (0 for #weight/#rir, 1 for the
 *                 rest), so every field falls back to its pinned default.
 */
async function corruptStoredControls(
  page: Page,
  mode: 'not-json' | 'non-numeric' | 'above-max' | 'below-min'
): Promise<void> {
  await page.evaluate(
    ({ key, mode }) => {
      if (mode === 'not-json') {
        sessionStorage.setItem(key, 'this-is-not-json');
        return;
      }
      const bogus: unknown =
        mode === 'non-numeric' ? 'abc' : mode === 'above-max' ? 999999 : -1;
      const raw = sessionStorage.getItem(key);
      let parsed: unknown;
      try {
        parsed = JSON.parse(raw ?? '');
      } catch {
        sessionStorage.setItem(key, String(bogus));
        return;
      }
      // Replace every primitive leaf, whatever the payload's shape.
      const walk = (node: unknown): void => {
        if (node !== null && typeof node === 'object') {
          const obj = node as Record<string, unknown>;
          for (const k of Object.keys(obj)) {
            const v = obj[k];
            if (v !== null && typeof v === 'object') walk(v);
            else obj[k] = bogus;
          }
        }
      };
      if (parsed !== null && typeof parsed === 'object') {
        walk(parsed);
        sessionStorage.setItem(key, JSON.stringify(parsed));
      } else {
        sessionStorage.setItem(key, String(bogus));
      }
    },
    { key: STORAGE_KEY, mode }
  );
}

async function selectFullBodyRoutine(page: Page): Promise<void> {
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

/** Select the first real exercise option (this applies its per-exercise recommendation). */
async function selectFirstExercise(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const select = document.getElementById('exercise') as HTMLSelectElement;
    return !!select && select.options.length > 1;
  });
  const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
  const value = await exerciseSelect.locator('option').nth(1).getAttribute('value');
  expect(value, 'expected at least one selectable exercise option').toBeTruthy();
  await exerciseSelect.selectOption(value as string);
}

/** Click Add Exercise and wait for the plan to actually gain a row (a SUCCESSFUL add). */
async function clickAddExercise(page: Page): Promise<void> {
  const rowsBefore = await page.locator('#workout_plan_table_body tr').count();
  await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
  await page.waitForFunction(
    (prev) => document.querySelectorAll('#workout_plan_table_body tr').length > prev,
    rowsBefore,
    { timeout: 10000 }
  );
}

/** Collect every primitive leaf of a parsed JSON payload, as normalized strings. */
function leafStrings(node: unknown, out: string[] = []): string[] {
  if (node !== null && typeof node === 'object') {
    for (const v of Object.values(node as Record<string, unknown>)) leafStrings(v, out);
  } else if (node !== undefined && node !== null) {
    const s = String(node);
    const n = Number(s);
    out.push(Number.isFinite(n) && s.trim() !== '' ? String(n) : s);
  }
  return out;
}

/**
 * Assert the ONE pinned record carries exactly the expected six values.
 *
 * Shape-agnostic within the pinned key: the payload is one JSON record, and every expected
 * value must appear among its primitive leaves (numerically normalized). Used by criterion 3
 * to prove the stored set holds the user's PRE-ADD values (Reading A, owner 2026-07-13).
 */
async function expectStoredControls(page: Page, expected: Controls): Promise<void> {
  const snapshot = await readStorage(page, 'session');
  const raw = snapshot[STORAGE_KEY];

  expect(
    raw,
    `expected the pinned record "${STORAGE_KEY}" to exist. sessionStorage: ${JSON.stringify(snapshot)}`
  ).toBeTruthy();

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`the record under "${STORAGE_KEY}" is not valid JSON: ${raw}`);
  }
  const leaves = leafStrings(parsed);

  for (const field of Object.keys(CONTROL_IDS) as (keyof Controls)[]) {
    const value = expected[field];
    const n = Number(value);
    const wanted = Number.isFinite(n) && value.trim() !== '' ? String(n) : value;
    expect(
      leaves,
      `the stored record must carry ${field}=${value} (record: ${raw})`
    ).toContain(wanted);
  }
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

  // KI-005 contract flip (criterion 10): this test previously asserted
  // "full reload resets Workout Controls to template defaults". Per the approved
  // acceptance criteria it now asserts restore-on-reload across ALL SIX controls
  // (criteria 1 + 2; TS-2 requires #rir and #rpe be asserted, not just sets/weight).
  test('full reload restores all six Workout Controls (criteria 1, 2)', async ({ page }) => {
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await waitForPageReady(page);

    // Mutate all six controls to values that differ from the template defaults
    await setAllControls(page, NON_DEFAULT_CONTROLS);

    // Hard reload — the new contract is that all six fields are restored
    await page.reload();
    await waitForPageReady(page);

    await expectControls(page, NON_DEFAULT_CONTROLS);
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

/* ========================================================================= *
 * KI-005 — Workout Controls persistence across reload
 *
 * PRE-IMPLEMENTATION ACCEPTANCE TESTS. Authored by `automation-qa` from the approved
 * acceptance criteria (docs/ki005_controls_persistence/PLANNING.md §0) and the four Gate 1
 * rulings — AR-3 (restored weight marks dirty), AR-4 (synchronous `input` capture, no
 * commit-on-blur), TS-7 (fallback = the six pinned defaults), OWNER-1 (hydration ordering).
 * They were written BEFORE any KI-005 implementation existed (Plan v2 Sequence Step 0,
 * blindness-by-sequencing) and are expected to be RED until it lands.
 *
 * Criterion → test map:
 *   1 + 2  restore all six on reload ......... "full reload restores all six Workout Controls"
 *          (in the Form State Persistence block above — it is the inverted contract test)
 *   1 (clarification / AR-4) ................. mid-entry value survives reload without blur
 *   3  (TS-3) ................................ PRE-ADD user values survive a successful Add
 *          (owner ruling 2026-07-13 — Reading A; Reading B rejected)
 *   4  (TS-4 / OWNER-1.4) .................... Clear Plan resets to defaults + key left ABSENT
 *   5  (TS-5) ................................ Clear Filters retains controls
 *   6  (TS-6) ................................ persisted to sessionStorage, not localStorage
 *   7  ....................................... routine cascade retains controls
 *   8  ....................................... saved values win over template defaults
 *   9  (TS-7) ................................ invalid stored values fall back to PINNED defaults
 *   OWNER-1.1/.2 ............................. pre-seeded record survives init (not clobbered)
 * ========================================================================= */
test.describe('UI Hardening — Workout Controls Persistence (KI-005)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    await resetWorkoutPlan(page);
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    // Start every case from an empty tab-scoped store so template defaults are what render.
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('criterion 1 (AR-4): mid-entry value survives reload even though focus never left the field', async ({
    page,
  }) => {
    // Type into #weight WITHOUT ever blurring/committing. `fill()` would emit `change`,
    // which is exactly what this case must NOT rely on — the owner ruled persistence is
    // driven by a synchronous `input` listener, so an un-blurred value must survive.
    const weight = page.locator(CONTROL_IDS.weight);
    await weight.click();
    await page.keyboard.press('ControlOrMeta+a');
    await weight.pressSequentially('137.5', { delay: 20 });

    // Prove no blur/commit happened: the field is still the active element.
    const stillFocused = await page.evaluate(
      () => (document.activeElement as HTMLElement | null)?.id === 'weight'
    );
    expect(stillFocused, 'the mid-entry field must still be focused (no blur/commit)').toBe(true);

    await page.reload();
    await waitForPageReady(page);

    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('137.5');
  });

  test('criterion 8: saved values win over the server-rendered template defaults', async ({
    page,
  }) => {
    // The template renders the pinned defaults on a clean load...
    await expectControls(page, PINNED_DEFAULTS);

    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await page.reload();
    await waitForPageReady(page);

    // ...and after reload the SAVED values must win over them.
    await expectControls(page, NON_DEFAULT_CONTROLS);
    const restored = await readAllControls(page);
    for (const field of Object.keys(CONTROL_IDS) as (keyof Controls)[]) {
      expect(restored[field], `saved ${field} must not have been reset to its default`).not.toBe(
        PINNED_DEFAULTS[field]
      );
    }
  });

  test('criterion 6 (TS-6): controls persist to sessionStorage, never localStorage', async ({
    page,
  }) => {
    const localBefore = await readStorage(page, 'local');

    await setAllControls(page, NON_DEFAULT_CONTROLS);

    // The record must exist under the pinned sessionStorage key (tab-scope proxy for
    // criterion 6 — tab close cannot be observed directly in Playwright).
    await readControlsRecord(page);

    // ...and nothing carrying those values — and no key of that name — may be written to
    // localStorage, which would survive tab close and violate the tab-scoped storage decision.
    const localAfter = await readStorage(page, 'local');
    expect(
      localAfter[STORAGE_KEY],
      `"${STORAGE_KEY}" must never be written to localStorage (criterion 6)`
    ).toBeUndefined();
    const localDelta = Object.entries(localAfter).filter(([k, v]) => localBefore[k] !== v);
    expect(
      JSON.stringify(localDelta),
      'Workout Controls must not be written to localStorage (criterion 6)'
    ).not.toContain(CONTROLS_SENTINEL);
  });

  test('OWNER-1.1/.2: a pre-seeded stored record survives init and is not clobbered by default population', async ({
    page,
  }) => {
    // Capture a real, app-authored payload (we never fabricate the record's internal shape).
    await setAllControls(page, NON_DEFAULT_CONTROLS);
    const payload = await readControlsRecord(page);

    // Re-seed that exact record BEFORE any page script runs on the next navigation, so the
    // stored record demonstrably pre-exists init (this is the hydration-ordering hazard).
    await page.evaluate(() => sessionStorage.clear());
    await page.addInitScript(
      ({ key, value }) => {
        window.sessionStorage.setItem(key, value);
      },
      { key: STORAGE_KEY, value: payload }
    );
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    // 1. Restore beat default population in the DOM.
    await expectControls(page, NON_DEFAULT_CONTROLS);

    // 2. Default population must not have overwritten the stored record either.
    const afterInit = await page.evaluate((k) => sessionStorage.getItem(k), STORAGE_KEY);
    expect(
      afterInit,
      'initial default population must not overwrite the pre-existing stored record (OWNER-1.1)'
    ).toBe(payload);
  });

  test('criterion 9 (TS-7): a non-JSON stored record falls back to the pinned defaults', async ({
    page,
  }) => {
    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await readControlsRecord(page);

    await corruptStoredControls(page, 'not-json');
    await page.reload();
    await waitForPageReady(page);

    await expectControls(page, PINNED_DEFAULTS);
  });

  test('criterion 9 (TS-7): non-numeric stored values fall back to the pinned defaults', async ({
    page,
  }) => {
    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await readControlsRecord(page);

    await corruptStoredControls(page, 'non-numeric');
    await page.reload();
    await waitForPageReady(page);

    await expectControls(page, PINNED_DEFAULTS);
  });

  // OWNER RULING (OWNER-5, 2026-07-13) — narrows what "out of range" MEANS in criterion 9.
  // Stored values are validated against the inputs' DECLARED min/max attributes and nothing
  // else; the module-invented caps (weight<=1000, sets<=50, min-rep/max-rep<=100) are DROPPED.
  // So a stored value is out of range iff it breaks a declared bound: the `max` of 10 on
  // #rir/#rpe, or the `min` on any of the six. #weight/#sets/#min_rep/#max_rep_range declare
  // NO max, so a corrupt 999999 restores into those fields — the owner's verbatim accepted
  // trade-off ("identical to typing 999999 without reloading, and the server still rejects it
  // at add time"). The criterion-9 FALLBACK TARGET is unchanged: the pinned defaults (TS-7).
  test('criterion 9 (TS-7 + OWNER-5): stored values outside the DECLARED min/max fall back to the pinned defaults', async ({
    page,
  }) => {
    // --- Above a declared `max`: bites on #rir/#rpe (max 10) and on nothing else. ---
    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await readControlsRecord(page);

    await corruptStoredControls(page, 'above-max');
    await page.reload();
    await waitForPageReady(page);

    await expectControls(page, {
      // No declared `max` → 999999 is NOT out of range → restores as stored (accepted trade-off).
      weight: '999999',
      sets: '999999',
      min_rep: '999999',
      max_rep_range: '999999',
      // Declared `max` 10 → out of range → falls back to the pinned default.
      rir: PINNED_DEFAULTS.rir,
      rpe: PINNED_DEFAULTS.rpe,
    });

    // --- Below a declared `min`: -1 breaks the `min` of ALL SIX → all six fall back. ---
    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await readControlsRecord(page);

    await corruptStoredControls(page, 'below-min');
    await page.reload();
    await waitForPageReady(page);

    await expectControls(page, PINNED_DEFAULTS);
  });

  // OWNER RULING (2026-07-13) — criterion 3 is READING A: the values the user entered BEFORE
  // Add must survive the add unchanged. Reading B ("persist whatever the post-success
  // reset/estimate path happens to display") is REJECTED. The post-success estimate/reset path
  // must NOT replace the user's values; only a later deliberate exercise selection may apply a
  // recommendation. NON_DEFAULT values are used throughout so a defaults-rendering-defaults
  // outcome cannot satisfy this vacuously.
  test('criterion 3 (TS-3): the PRE-ADD user values survive a successful Add Exercise (Reading A)', async ({
    page,
  }) => {
    await selectFullBodyRoutine(page);
    // Select first, so the per-exercise recommendation lands BEFORE the user's own values.
    await selectFirstExercise(page);
    await setAllControls(page, NON_DEFAULT_CONTROLS);

    await clickAddExercise(page);

    // 1. The six PRE-ADD values are still DISPLAYED after the successful add.
    await expectControls(page, NON_DEFAULT_CONTROLS);

    // 2. The pinned record carries those same pre-Add values (no divergence, not reset values).
    await expectStoredControls(page, NON_DEFAULT_CONTROLS);

    // 3. And they are still there after a reload.
    await page.reload();
    await waitForPageReady(page);
    await expectControls(page, NON_DEFAULT_CONTROLS);
  });

  test('criterion 4 (TS-4 / OWNER-1.4): Clear Plan resets the six controls to defaults and leaves the storage key ABSENT', async ({
    page,
  }) => {
    await selectFullBodyRoutine(page);
    await selectFirstExercise(page);
    await clickAddExercise(page);

    await setAllControls(page, NON_DEFAULT_CONTROLS);
    await readControlsRecord(page);

    // Confirm Clear Plan through the modal (the single #clear-plan-btn path — AR-5).
    // Wait for Bootstrap's `shown.bs.modal` before clicking Confirm: calling hide() while the
    // show transition is still in flight is swallowed by Bootstrap and the modal never closes.
    // (Test-synchronization only — the assertions below are unchanged.)
    const shown = page.evaluate(
      () =>
        new Promise<void>((resolve) => {
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
        })
    );
    await page.locator('#clear-plan-btn').click();
    await shown;
    await page.locator('#confirmClearPlanBtn').click();
    await expect(page.locator('#clearPlanModal')).not.toHaveClass(/show/, { timeout: 5000 });

    // 1. The six controls are immediately restored to the pinned template defaults.
    await expectControls(page, PINNED_DEFAULTS);

    // 2. The storage key is REMOVED — not re-saved with the defaults (OWNER-1.4).
    const stored = await page.evaluate((k) => sessionStorage.getItem(k), STORAGE_KEY);
    expect(
      stored,
      `Clear Plan must leave "${STORAGE_KEY}" absent, not re-save the defaults (OWNER-1.4)`
    ).toBeNull();

    // 3. And the reset survives a reload (nothing lingering to restore).
    await page.reload();
    await waitForPageReady(page);
    await expectControls(page, PINNED_DEFAULTS);
  });

  test('criterion 5 (TS-5): Clear Filters retains the six controls', async ({ page }) => {
    await setAllControls(page, NON_DEFAULT_CONTROLS);

    await page.locator(SELECTORS.CLEAR_FILTERS_BTN).click();

    // Retained in the DOM...
    await expectControls(page, NON_DEFAULT_CONTROLS);

    // ...and still retained in storage (a reload proves they were not cleared).
    await page.reload();
    await waitForPageReady(page);
    await expectControls(page, NON_DEFAULT_CONTROLS);
  });

  test('criterion 7: the routine cascade retains all six controls', async ({ page }) => {
    await setAllControls(page, NON_DEFAULT_CONTROLS);

    await selectFullBodyRoutine(page);

    // One global set per tab — the cascade must not touch the controls...
    await expectControls(page, NON_DEFAULT_CONTROLS);

    // ...and the stored set must still be intact afterwards.
    await page.reload();
    await waitForPageReady(page);
    await expectControls(page, NON_DEFAULT_CONTROLS);
  });
});

/* ========================================================================= *
 * KI-005 — Gate 1 amendment #3 (OWNER-9 / OWNER-10 + authorized correctness
 * cleanup (b)). Authored at Sequence Step 17, BEFORE the corrective
 * implementation exists (blindness-by-sequencing). Every assertion below is
 * derived from the OWNER-9 / OWNER-10 / AR-3 RULING TEXT in
 * docs/ki005_controls_persistence/PLANNING.md — never from an implementation.
 *
 * OWNER-9 (required behavior, verbatim): after Apply Suggestion / ± nudge /
 * Reset to Suggestion / learned reset / ignore-transfer, "the displayed six
 * controls and the hypertrophy_workout_controls_v1 record MATCH, and a reload
 * restores the NEWLY DISPLAYED values."
 *
 * OWNER-10 (required behavior): when NO exercise is selected, the six controls
 * and their sessionStorage record remain unchanged; Apply Suggestion, the ±
 * nudges, Reset to Suggestion and the learned actions must NOT remain operable
 * against a phantom prior exercise; stale estimate-only UI must be NEUTRALIZED
 * (no claim about the previous exercise). Re-scoped OWNER-8: the ancillary
 * estimate UI must ALSO be neutralized after a successful Add Exercise —
 * neutral wording such as "current values" is acceptable, a FALSE SOURCE CLAIM
 * is not.
 *
 * AR-3 (authorized correctness cleanup (b) — zero coverage until now): a
 * restored #weight stays protected by the dirty-state behavior and must not be
 * clobbered by an UNRELATED estimate re-apply (a deliberate NEW exercise
 * selection may still reset the flag and apply that exercise's recommendation).
 *
 * NON-VACUITY DISCIPLINE (deliberate, and load-bearing): every "must be
 * neutralized / must not be operable" assertion is preceded by a PRE-STATE
 * GUARD that proves the surface is currently rendered, visible, and carrying
 * the claim it must later stop making. Without that guard a `toBeHidden()`
 * would pass for free on any element that simply never rendered (e.g.
 * #weight-hand-hint is `hidden` in the template unless the estimate is
 * is_dumbbell, and #workout-estimate-trace is hidden until "show the math" is
 * opened). The mocks below therefore deliberately produce an is_dumbbell,
 * learned-source estimate carrying an advisory fatigue block, so ALL of the
 * estimate-only surfaces named in the OWNER-10 ruling are demonstrably live
 * before the transition under test.
 * ========================================================================= */

const ESTIMATE_API = '/api/user_profile/estimate';
const CALIBRATION_RESET_API = '/api/user_profile/calibration/reset';
const CALIBRATION_IGNORE_API = '/api/user_profile/calibration/ignore_transfer';

/** The advisory fatigue-context block — what makes the ± nudge / Reset-to-suggestion row render. */
const FATIGUE_CONTEXT = {
  enabled: true,
  muscle: 'Chest',
  muscle_label: 'Chest',
  has_landmarks: true,
  source: 'both',
  period: 'this_week',
  period_label: 'This week (Mon–Sun)',
  planned: { band: 'moderate', percent_of_mrv: 60, has_landmarks: true },
  logged: { band: 'moderate', percent_of_mrv: 58, has_landmarks: true },
  disagree: false,
  is_advisory_fallback: false,
  headline: 'Chest fatigue: moderate.',
  advisory: 'This does not change your suggestion.',
};

/**
 * A LEARNED, is_dumbbell estimate carrying the advisory fatigue block — so every estimate-only
 * surface OWNER-10 names is live: provenance (claims "learned"), learned badge, fatigue chip,
 * the per-hand weight hint (is_dumbbell), the trace, AND both families of action controls
 * (learned Apply/Keep/Reset + the ± nudges and Reset-to-suggestion).
 */
const LEARNED_ESTIMATE = {
  ok: true,
  status: 'success',
  data: {
    weight: 60,
    sets: 4,
    min_rep: 6,
    max_rep: 8,
    rir: 3,
    rpe: 7,
    source: 'learned',
    reason: 'learned_calibration',
    is_dumbbell: true,
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
      ],
    },
    fatigue_context: FATIGUE_CONTEXT,
  },
};

/** What the estimate chain falls back to once the learned row is reset / the transfer ignored. */
const FALLBACK_ESTIMATE = {
  ok: true,
  status: 'success',
  data: {
    weight: 47.5,
    sets: 2,
    min_rep: 9,
    max_rep: 12,
    rir: 2,
    rpe: 8,
    source: 'log',
    is_dumbbell: false,
    trace: {
      source: 'log',
      steps: [{ label: 'From your last logged set', value: '47.5 kg × 9–12' }],
    },
    fatigue_context: FATIGUE_CONTEXT,
  },
};

/** A related-exercise (transfer) estimate — the one whose transfer can be IGNORED. */
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
          detail: '4 scored logs, confidence: high.',
        },
      ],
    },
    fatigue_context: FATIGUE_CONTEXT,
  },
};

/** Any wording that CLAIMS a source for the displayed values (OWNER-10 forbids a false one). */
const SOURCE_CLAIM =
  /from your profile|from your last set|population estimate|related exercise|learned/i;

/** Every estimate-only action control that OWNER-10 says must not act on a de-selected exercise. */
const ESTIMATE_ACTION_SELECTORS: Record<string, string> = {
  'Apply Suggestion': '[data-learned-apply]',
  'Keep current (learned)': '[data-learned-keep]',
  'Reset learned': '[data-learned-reset]',
  '± nudge buttons': '[data-nudge]',
  'Reset to suggestion': '[data-fatigue-nudge-reset]',
};

/**
 * The read-only estimate-only surfaces, each with the CLAIM it makes about the exercise the
 * estimate was computed for. `claim` is asserted PRESENT before the transition (non-vacuity)
 * and ABSENT after (the OWNER-10 contract: "must no longer claim ... the previous exercise").
 *
 * "Neutralized" is satisfied by hiding/clearing the surface OR by re-rendering it without the
 * claim — the ruling permits either (it only forbids a FALSE claim), so these assertions do not
 * over-constrain the implementer into one of the two.
 */
const ESTIMATE_CLAIM_SURFACES: { label: string; selector: string; claim: RegExp }[] = [
  { label: 'learned badge', selector: '#workout-estimate-learned-badge', claim: /learn/i },
  { label: 'fatigue chip', selector: '#workout-estimate-fatigue-chip', claim: /fatigue/i },
  { label: 'weight hand hint', selector: '#weight-hand-hint', claim: /per hand/i },
  { label: 'estimate trace', selector: '#workout-estimate-trace', claim: /logged set|learned/i },
];

/**
 * PRE-STATE GUARD. Proves — before the transition under test — that every surface OWNER-10
 * names is live and claiming the selected exercise, and that every estimate action control is
 * rendered and operable. If this ever fails, the case is BROKEN (bad mock/selector), not red:
 * that distinction is exactly what the Step-17 evidence has to be able to make.
 */
async function expectEstimateStateLiveAndClaiming(page: Page): Promise<void> {
  const provenance = page.locator('#workout-estimate-provenance');
  await expect(provenance, 'PRE-STATE: the provenance line must claim a source').toBeVisible();
  await expect(provenance).toHaveText(SOURCE_CLAIM);

  for (const { label, selector, claim } of ESTIMATE_CLAIM_SURFACES) {
    const loc = page.locator(selector);
    await expect(loc, `PRE-STATE: the ${label} must be visible while an exercise IS selected`)
      .toBeVisible();
    await expect(loc, `PRE-STATE: the ${label} must be claiming the selected exercise`)
      .toHaveText(claim);
  }

  for (const [label, selector] of Object.entries(ESTIMATE_ACTION_SELECTORS)) {
    const loc = page.locator(selector).first();
    await expect(loc, `PRE-STATE: ${label} must be rendered while an exercise IS selected`)
      .toBeVisible();
    await expect(loc, `PRE-STATE: ${label} must be operable while an exercise IS selected`)
      .toBeEnabled();
  }
}

/** Hidden OR disabled OR absent — the ruling allows any of the three; operable is the failure. */
async function expectNotOperable(page: Page, selector: string, label: string): Promise<void> {
  const loc = page.locator(selector);
  const count = await loc.count();
  for (let i = 0; i < count; i++) {
    const el = loc.nth(i);
    const operable = (await el.isVisible()) && (await el.isEnabled());
    expect(
      operable,
      `${label} must be hidden or disabled — it must not stay operable against an exercise ` +
        `that is no longer selected (OWNER-10)`
    ).toBe(false);
  }
}

/**
 * The OWNER-10 neutralization contract: no estimate-only surface may still claim the exercise
 * the estimate was computed for. Hidden/cleared passes; visible-but-neutral passes; visible and
 * still claiming FAILS.
 */
async function expectEstimateStateNeutralized(page: Page, context: string): Promise<void> {
  const provenance = page.locator('#workout-estimate-provenance');
  if (await provenance.isVisible()) {
    const text = (await provenance.textContent())?.trim() ?? '';
    expect(
      text,
      `${context}: the provenance line must not claim a source for the displayed values ` +
        `(OWNER-10 — neutral wording such as "current values" is fine; a false source claim is not)`
    ).not.toMatch(SOURCE_CLAIM);
  }

  for (const { label, selector, claim } of ESTIMATE_CLAIM_SURFACES) {
    const loc = page.locator(selector);
    if (!(await loc.isVisible())) continue; // hidden or cleared → neutralized
    const text = (await loc.textContent())?.trim() ?? '';
    expect(
      text,
      `${context}: the ${label} must be neutralized — it may not keep describing the exercise ` +
        `the estimate was computed for (OWNER-10)`
    ).not.toMatch(claim);
  }
}

/** Route the estimate endpoint at a mutable body, so learned-reset / ignore-transfer can flip it. */
async function mockEstimate(page: Page, body: () => unknown): Promise<void> {
  await page.route(`**${ESTIMATE_API}**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body()),
    });
  });
}

/** Deliberately select an exercise and wait for its estimate to land. */
async function selectExerciseWithEstimate(page: Page): Promise<void> {
  await selectFullBodyRoutine(page);
  const estimateDone = page.waitForResponse((r) => r.url().includes(ESTIMATE_API));
  await selectFirstExercise(page);
  await estimateDone;
}

/** Open "show the math" — the learned actions and the ± nudge row both live inside the trace. */
async function openEstimateTrace(page: Page): Promise<void> {
  const toggle = page.locator('#workout-estimate-trace-toggle');
  await expect(toggle, 'the estimate trace toggle must render for a learned estimate').toBeVisible();
  await toggle.click();
  await expect(page.locator('#workout-estimate-trace')).toBeVisible();
}

/**
 * The OWNER-9 contract, asserted identically for every estimate-driven control write: whatever
 * the action put on screen is what storage holds, and what a reload brings back. Reading the DOM
 * (rather than hardcoding post-action numbers) binds the assertion to the RULING — "the NEWLY
 * DISPLAYED values" — instead of to any implementation's arithmetic.
 */
async function expectDisplayedValuesPersistAcrossReload(page: Page): Promise<void> {
  const displayed = await readAllControls(page);

  // 1. Storage MATCHES what is displayed (no DOM/storage desync).
  await expectStoredControls(page, displayed);

  // 2. A reload restores the NEWLY DISPLAYED values.
  await page.reload();
  await waitForPageReady(page);
  await expectControls(page, displayed);
}

test.describe('UI Hardening — Estimate actions persist (KI-005 / OWNER-9)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    await resetWorkoutPlan(page);
    consoleErrors.startCollecting();
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  /** Shared arrival: learned estimate mocked, clean tab-scoped store, plan page ready. */
  async function arriveOnWorkoutPlan(page: Page): Promise<void> {
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await waitForPageReady(page);
  }

  test('OWNER-9: Apply Suggestion → the applied values survive a reload', async ({ page }) => {
    await mockEstimate(page, () => LEARNED_ESTIMATE);
    await arriveOnWorkoutPlan(page);
    await selectExerciseWithEstimate(page);
    // The learned Apply / Keep / Reset row is rendered inside "show the math".
    await openEstimateTrace(page);

    // The user types their own weight FIRST, so a stale record cannot pass by coincidence:
    // storage now demonstrably holds 70, and Apply must move BOTH the DOM and the record.
    await page.fill(CONTROL_IDS.weight, '70');
    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('70');
    await expectStoredControls(page, { ...(await readAllControls(page)) });

    const apply = page.locator('[data-learned-apply]');
    await expect(apply, 'the learned Apply Suggestion action must render').toBeVisible();
    await apply.click();

    // Non-vacuity: the action genuinely changed the displayed value.
    await expect(page.locator(CONTROL_IDS.weight)).not.toHaveValue('70');

    await expectDisplayedValuesPersistAcrossReload(page);
  });

  test('OWNER-9: ± nudge → the nudged values survive a reload', async ({ page }) => {
    await mockEstimate(page, () => LEARNED_ESTIMATE);
    await arriveOnWorkoutPlan(page);
    await selectExerciseWithEstimate(page);
    await openEstimateTrace(page);

    const nudge = page.locator('#workout-estimate-trace [data-fatigue-nudge]');
    await expect(nudge, 'the ± nudge affordance must render inside the trace').toBeVisible();

    // Seed a record from a real user edit, so the case cannot fail merely for want of a record.
    await page.fill(CONTROL_IDS.weight, '70');
    await expectStoredControls(page, { ...(await readAllControls(page)) });

    const weightBefore = await page.locator(CONTROL_IDS.weight).inputValue();
    const setsBefore = await page.locator(CONTROL_IDS.sets).inputValue();

    await nudge.locator('[data-nudge="weight"][data-nudge-dir="up"]').click();
    await nudge.locator('[data-nudge="sets"][data-nudge-dir="down"]').click();

    // Non-vacuity: the nudges genuinely moved the displayed values.
    await expect(page.locator(CONTROL_IDS.weight)).not.toHaveValue(weightBefore);
    await expect(page.locator(CONTROL_IDS.sets)).not.toHaveValue(setsBefore);

    await expectDisplayedValuesPersistAcrossReload(page);
  });

  test('OWNER-9: Reset to Suggestion → the reset values survive a reload', async ({ page }) => {
    await mockEstimate(page, () => LEARNED_ESTIMATE);
    await arriveOnWorkoutPlan(page);
    await selectExerciseWithEstimate(page);
    await openEstimateTrace(page);

    const nudge = page.locator('#workout-estimate-trace [data-fatigue-nudge]');
    await expect(nudge).toBeVisible();

    // The user types over the suggestion (so storage holds 120), then resets back to it.
    await page.fill(CONTROL_IDS.weight, '120');
    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('120');
    await expectStoredControls(page, { ...(await readAllControls(page)) });

    await nudge.locator('[data-fatigue-nudge-reset]').click();

    // Non-vacuity: the reset genuinely moved the displayed value back off the typed one.
    await expect(page.locator(CONTROL_IDS.weight)).not.toHaveValue('120');

    await expectDisplayedValuesPersistAcrossReload(page);
  });

  // OWNER-9 names learned reset and ignore-transfer explicitly ("applyEstimateToWorkoutControls()
  // ... covering learned reset / ignore-transfer AND ordinary estimate application"). Both ARE
  // drivable from a spec — e2e/learned-calibration.spec.ts already clicks [data-learned-reset]
  // and [data-related-ignore] against a mutable mocked estimate — so neither is dropped here.
  test('OWNER-9: learned reset → the re-applied fallback values survive a reload', async ({
    page,
  }) => {
    let learnedActive = true;
    await mockEstimate(page, () => (learnedActive ? LEARNED_ESTIMATE : FALLBACK_ESTIMATE));
    await page.route(`**${CALIBRATION_RESET_API}`, async (route) => {
      learnedActive = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, status: 'success', data: {} }),
      });
    });

    await arriveOnWorkoutPlan(page);
    await selectExerciseWithEstimate(page);
    await openEstimateTrace(page);

    const weightBefore = await page.locator(CONTROL_IDS.weight).inputValue();

    // Reset the learned row → the estimate chain re-fetches and RE-APPLIES the fallback into
    // the six controls. That write is inside the OWNER-9 fix surface.
    const resetDone = page.waitForResponse((r) => r.url().includes(CALIBRATION_RESET_API));
    const refetch = page.waitForResponse((r) => r.url().includes(ESTIMATE_API));
    await page.locator('[data-learned-reset]').click();
    await resetDone;
    await refetch;

    // Non-vacuity: the re-applied fallback genuinely changed the displayed values.
    await expect(page.locator(CONTROL_IDS.weight)).not.toHaveValue(weightBefore);

    await expectDisplayedValuesPersistAcrossReload(page);
  });

  test('OWNER-9: ignore-transfer → the re-applied fallback values survive a reload', async ({
    page,
  }) => {
    let relatedActive = true;
    await mockEstimate(page, () => (relatedActive ? RELATED_ESTIMATE : FALLBACK_ESTIMATE));
    await page.route(`**${CALIBRATION_IGNORE_API}`, async (route) => {
      relatedActive = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, status: 'success', data: {} }),
      });
    });

    await arriveOnWorkoutPlan(page);
    await selectExerciseWithEstimate(page);
    await openEstimateTrace(page);

    const weightBefore = await page.locator(CONTROL_IDS.weight).inputValue();

    const ignoreDone = page.waitForResponse((r) => r.url().includes(CALIBRATION_IGNORE_API));
    const refetch = page.waitForResponse((r) => r.url().includes(ESTIMATE_API));
    await page.locator('[data-related-ignore]').click();
    await ignoreDone;
    await refetch;

    // Non-vacuity: ignoring the transfer genuinely changed the displayed values.
    await expect(page.locator(CONTROL_IDS.weight)).not.toHaveValue(weightBefore);

    await expectDisplayedValuesPersistAcrossReload(page);
  });
});

test.describe('UI Hardening — Estimate state is neutral, not falsely attributed (KI-005 / OWNER-10)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    await resetWorkoutPlan(page);
    await mockEstimate(page, () => LEARNED_ESTIMATE);
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('OWNER-10: an empty selection leaves the six controls + the stored record untouched, and its estimate state is neutralized', async ({
    page,
  }) => {
    await selectExerciseWithEstimate(page);
    // Open the trace, then PROVE every estimate-only surface is live and every action control is
    // operable BEFORE the selection is cleared. Without this guard the assertions after the
    // clear could pass for free on a surface that never rendered at all.
    await openEstimateTrace(page);
    await expectEstimateStateLiveAndClaiming(page);

    await setAllControls(page, NON_DEFAULT_CONTROLS);
    const recordBefore = await readControlsRecord(page);

    // Clear Filters empties the exercise dropdown → the empty-selection state.
    await page.locator(SELECTORS.CLEAR_FILTERS_BTN).click();
    await expect(page.locator(SELECTORS.EXERCISE_SEARCH)).toHaveValue('');

    // 1. The six controls are untouched...
    await expectControls(page, NON_DEFAULT_CONTROLS);

    // 2. ...and so is the stored record, byte-for-byte.
    const recordAfter = await page.evaluate((k) => sessionStorage.getItem(k), STORAGE_KEY);
    expect(
      recordAfter,
      'an empty selection must not write to the stored controls record (OWNER-10)'
    ).toBe(recordBefore);

    // 3. No estimate action may remain operable against the de-selected exercise. (This is the
    //    live defect OWNER-10 records: QA typed 55, clicked "Reset to suggestion" with NOTHING
    //    selected, and #weight was overwritten to the de-selected exercise's 26.)
    for (const [label, selector] of Object.entries(ESTIMATE_ACTION_SELECTORS)) {
      await expectNotOperable(page, selector, label);
    }

    // 4. And the stale estimate-only UI may not keep claiming the de-selected exercise.
    await expectEstimateStateNeutralized(page, 'with NO exercise selected');
  });

  test('OWNER-10 / re-scoped OWNER-8: after a successful Add Exercise the estimate state is NEUTRAL, not falsely attributed', async ({
    page,
  }) => {
    await selectExerciseWithEstimate(page);
    await openEstimateTrace(page);
    await expectEstimateStateLiveAndClaiming(page);

    // The user OVERRIDES the weight, then adds — Reading A keeps their value, so the estimate
    // metadata no longer describes what is displayed and must not claim to.
    await page.fill(CONTROL_IDS.weight, '137.5');
    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('137.5');

    await clickAddExercise(page);

    // Reading A still holds (criterion 3): the user's pre-add value is retained.
    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('137.5');

    // ...and the estimate-only UI must NOT claim it produced that value.
    await expectEstimateStateNeutralized(page, 'after a successful Add Exercise');
  });
});

test.describe('UI Hardening — AR-3 restored-weight dirty-state regression (KI-005)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    await resetWorkoutPlan(page);
    await mockEstimate(page, () => LEARNED_ESTIMATE);
    consoleErrors.startCollecting();
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('AR-3: a RESTORED #weight is not clobbered by an unrelated estimate re-apply', async ({
    page,
  }) => {
    await selectExerciseWithEstimate(page);

    // The user overrides the estimate with their own weight, which persists...
    await page.fill(CONTROL_IDS.weight, '137.5');
    await readControlsRecord(page);

    // ...and is RESTORED on reload (criterion 8). Per the AR-3 ruling, restoring a valid saved
    // #weight must mark it user-dirty, so an unrelated estimate re-apply cannot overwrite it.
    await page.reload();
    await waitForPageReady(page);
    await expect(page.locator(CONTROL_IDS.weight)).toHaveValue('137.5');

    // An UNRELATED estimate re-apply: point the estimate at an exercise WITHOUT a deliberate
    // selection event (no `change` → no dirty reset), then re-apply the estimate. A deliberate
    // NEW selection is explicitly ALLOWED to reset the flag and overwrite — this is the path
    // AR-3 says must NOT. (`applyUserProfileEstimateForSelectedExercise` is an existing public
    // export of workout-plan.js — the same module seam this spec already uses for toast.js.)
    const exerciseName = await page.evaluate(() => {
      const select = document.getElementById('exercise') as HTMLSelectElement | null;
      const option = select?.options[1];
      if (select && option) select.value = option.value; // NO change event dispatched
      return option?.value ?? '';
    });
    expect(exerciseName, 'expected a selectable exercise option').toBeTruthy();

    const reapplied = page.waitForResponse((r) => r.url().includes(ESTIMATE_API));
    await page.evaluate(async () => {
      const mod = await import('/static/js/modules/workout-plan.js');
      await mod.applyUserProfileEstimateForSelectedExercise();
    });
    await reapplied;

    // The restored weight is still the user's — the estimate's 60 did not clobber it.
    await expect(
      page.locator(CONTROL_IDS.weight),
      'a restored #weight must stay protected by the AR-3 dirty-state behavior'
    ).toHaveValue('137.5');

    // POSITIVE CONTROL — this is what makes the assertion above NON-VACUOUS. It proves the
    // estimate-apply path CAN write #weight in this exact page state: a DELIBERATE new exercise
    // selection resets the dirty flag and applies that exercise's recommendation (the AR-3
    // carve-out, explicitly allowed). Had restore NOT marked #weight dirty, the unrelated
    // re-apply above would have overwritten 137.5 with the estimate's 60 exactly as this does.
    const otherExercise = await page
      .locator(SELECTORS.EXERCISE_SEARCH)
      .locator('option')
      .nth(2)
      .getAttribute('value');
    expect(otherExercise, 'expected a second selectable exercise option').toBeTruthy();

    const deliberateEstimate = page.waitForResponse((r) => r.url().includes(ESTIMATE_API));
    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption(otherExercise as string);
    await deliberateEstimate;

    await expect(
      page.locator(CONTROL_IDS.weight),
      'a DELIBERATE new exercise selection MAY reset the dirty flag and apply that exercise\'s ' +
        'recommendation (AR-3 carve-out) — and it must, or the case above would be vacuous'
    ).toHaveValue('60');
  });
});
