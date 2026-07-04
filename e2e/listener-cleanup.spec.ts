/**
 * E2E Regression: event-listener cleanup (Track A6)
 *
 * Instruments EventTarget.prototype.addEventListener/removeEventListener via an
 * init script (mirroring the browser's duplicate-registration semantics) to
 * count LIVE document 'click' and window 'scroll'/'resize' listeners, then
 * asserts:
 *
 * 1. Execution-style picker — while a picker is open, exactly ONE live
 *    document click listener belongs to it, no matter how many previous
 *    pickers were dismissed via Cancel/Close or replaced by re-clicking the
 *    cell. Before the A6 fix, only the outside-click dismissal path removed
 *    the document-level closeOnOutside listener; Close/Cancel/Save and
 *    picker replacement each stranded one stale listener, so the while-open
 *    live count read 2+ (stale listeners only self-purged on a later
 *    unrelated document click, firing extra handler work each time).
 *
 * 2. Workout dropdowns — when an enhanced select's .wpdd container is removed
 *    from the DOM (as happens when the owning markup is re-rendered), its
 *    window scroll/resize listeners, document click listener, and
 *    body-appended .wpdd-popover are torn down via _cleanupHandler. Before
 *    the A6 fix, _cleanupHandler existed but was never invoked.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';

const TEST_ROUTINE = 'GYM - Full Body - Workout A';

type ListenerCounters = { docClick: number; winScroll: number; winResize: number };

/** Install listener accounting before any page script runs. */
async function instrumentListeners(page: import('@playwright/test').Page): Promise<void> {
  await page.addInitScript(() => {
    type Entry = { type: string; listener: unknown; capture: boolean };
    const counters = { docClick: 0, winScroll: 0, winResize: 0 };
    (window as unknown as { __liveListeners: typeof counters }).__liveListeners = counters;
    const registry: { doc: Entry[]; win: Entry[] } = { doc: [], win: [] };

    const scopeOf = (target: EventTarget): 'doc' | 'win' | null =>
      target === document ? 'doc' : target === window ? 'win' : null;
    const captureOf = (options: unknown): boolean =>
      typeof options === 'boolean'
        ? options
        : Boolean((options as AddEventListenerOptions | undefined)?.capture);
    const bump = (scope: 'doc' | 'win', type: string, delta: number): void => {
      if (scope === 'doc' && type === 'click') counters.docClick += delta;
      if (scope === 'win' && type === 'scroll') counters.winScroll += delta;
      if (scope === 'win' && type === 'resize') counters.winResize += delta;
    };

    const origAdd = EventTarget.prototype.addEventListener;
    const origRemove = EventTarget.prototype.removeEventListener;
    EventTarget.prototype.addEventListener = function (
      type: string,
      listener: EventListenerOrEventListenerObject | null,
      options?: boolean | AddEventListenerOptions
    ) {
      const scope = scopeOf(this);
      if (scope && listener) {
        const capture = captureOf(options);
        const exists = registry[scope].some(
          (e) => e.type === type && e.listener === listener && e.capture === capture
        );
        if (!exists) {
          registry[scope].push({ type, listener, capture });
          bump(scope, type, 1);
        }
      }
      return origAdd.call(this, type, listener, options);
    };
    EventTarget.prototype.removeEventListener = function (
      type: string,
      listener: EventListenerOrEventListenerObject | null,
      options?: boolean | EventListenerOptions
    ) {
      const scope = scopeOf(this);
      if (scope && listener) {
        const capture = captureOf(options);
        const idx = registry[scope].findIndex(
          (e) => e.type === type && e.listener === listener && e.capture === capture
        );
        if (idx >= 0) {
          registry[scope].splice(idx, 1);
          bump(scope, type, -1);
        }
      }
      return origRemove.call(this, type, listener, options);
    };
  });
}

async function readCounters(page: import('@playwright/test').Page): Promise<ListenerCounters> {
  return page.evaluate(
    () => (window as unknown as { __liveListeners: ListenerCounters }).__liveListeners,
  );
}

async function selectRoutine(page: import('@playwright/test').Page): Promise<void> {
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
}

/** Make sure the test routine has at least one plan row (adds one via API if empty). */
async function ensureExerciseRow(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext
): Promise<void> {
  await selectRoutine(page);
  const rowLocator = page.locator('#workout_plan_table_body tr');
  if ((await rowLocator.count()) > 0) {
    return;
  }

  const allResponse = await request.get('/get_all_exercises');
  const allPayload: unknown = await allResponse.json().catch(() => ({}));
  const rows: unknown[] = Array.isArray(allPayload)
    ? allPayload
    : Array.isArray((allPayload as { data?: unknown[] }).data)
      ? ((allPayload as { data: unknown[] }).data)
      : [];
  const first = rows
    .map((row) => {
      if (typeof row === 'string') return row;
      const candidate = row as Record<string, unknown>;
      const raw = candidate.exercise ?? candidate.exercise_name ?? candidate.name;
      return typeof raw === 'string' ? raw : null;
    })
    .find((name): name is string => Boolean(name && name.trim()));
  expect(first, 'seeded DB should expose at least one exercise').toBeTruthy();

  const addResponse = await request.post('/add_exercise', {
    data: {
      routine: TEST_ROUTINE,
      exercise: first,
      sets: 3,
      min_rep_range: 8,
      max_rep_range: 12,
      weight: 100,
      rir: 2,
    },
  });
  expect(addResponse.ok()).toBe(true);

  await page.reload();
  await waitForPageReady(page);
  await selectRoutine(page);
  await page.waitForSelector('#workout_plan_table_body tr');
}

/** Open the execution-style picker and wait until its outside-click listener is armed (100ms timer). */
async function openPicker(page: import('@playwright/test').Page): Promise<void> {
  await page.locator('.execution-style-cell').first().click();
  await expect(page.locator('.execution-style-picker')).toHaveCount(1);
  await page.waitForTimeout(200);
}

test.describe('Listener cleanup regressions (Track A6)', () => {
  test.beforeEach(async ({ page, request, consoleErrors }) => {
    consoleErrors.startCollecting();
    await instrumentListeners(page);
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);
    await ensureExerciseRow(page, request);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('execution-style picker: every dismissal path releases its document listener', async ({ page }) => {
    // Warm-up cycle so one-time lazy listeners don't skew the baseline, then a
    // neutral document click to purge any pre-existing stale handlers (pre-fix
    // stale closeOnOutside listeners self-remove on such a click).
    await openPicker(page);
    await page.locator('.execution-style-picker .btn-cancel-exec').click();
    await expect(page.locator('.execution-style-picker')).toHaveCount(0);
    await page.evaluate(() => document.body.click());

    const base = await readCounters(page);

    // While the picker is open, exactly one live document click listener may
    // belong to it. Pre-fix, every cycle after the first read one extra stale
    // listener stranded by Cancel, Close, or Save. Outside click was the only
    // path that cleaned itself up correctly.
    const dismissals = ['cancel', 'close', 'save', 'outside', 'cancel'] as const;
    const whileOpenDeltas: number[] = [];
    for (const dismissal of dismissals) {
      await openPicker(page);
      const open = await readCounters(page);
      whileOpenDeltas.push(open.docClick - base.docClick);

      if (dismissal === 'outside') {
        await page.locator('h1').click();
      } else {
        await page.locator(`.execution-style-picker .btn-${dismissal}-exec, ` +
          `.execution-style-picker .btn-${dismissal}-picker`).click();
      }
      await expect(page.locator('.execution-style-picker')).toHaveCount(0);

      const closed = await readCounters(page);
      expect(
        closed.docClick - base.docClick,
        `${dismissal} dismissal must release its document click listener`,
      ).toBe(0);
    }

    expect(
      whileOpenDeltas,
      'each open picker must own exactly one live document click listener',
    ).toEqual([1, 1, 1, 1, 1]);
  });

  test('execution-style picker: reopening while open replaces the picker without leaking listeners', async ({ page }) => {
    // Warm-up cycle + neutral click for a stable baseline (see above).
    await openPicker(page);
    await page.locator('.execution-style-picker .btn-cancel-exec').click();
    await expect(page.locator('.execution-style-picker')).toHaveCount(0);
    await page.evaluate(() => document.body.click());

    const base = await readCounters(page);

    // Re-clicking the cell while a picker is open replaces the picker element.
    // Clicks on .execution-style-cell are exempt from the outside-click close
    // logic, so pre-fix each replacement stranded a listener that could not
    // self-purge during cell-only click sequences: live count grew to N+1.
    await openPicker(page);
    for (let i = 0; i < 4; i++) {
      await openPicker(page);
    }
    await expect(page.locator('.execution-style-picker')).toHaveCount(1);

    const open = await readCounters(page);
    expect(
      open.docClick - base.docClick,
      'replaced pickers must not strand their outside-click document listeners',
    ).toBe(1);

    await page.locator('.execution-style-picker .btn-cancel-exec').click();
    await expect(page.locator('.execution-style-picker')).toHaveCount(0);
  });

  test('workout dropdowns: removing an enhanced select tears down its listeners and popover', async ({ page }) => {
    // The exercise <select> is progressively enhanced into a .wpdd wrapper with
    // a body-appended popover plus window/document listeners.
    await page.waitForSelector('#exercise');
    await page.waitForFunction(() => {
      const select = document.getElementById('exercise');
      return Boolean(select && select.closest('.wpdd'));
    });

    const base = await readCounters(page);
    const basePopovers = await page.evaluate(
      () => document.querySelectorAll('.wpdd-popover').length,
    );

    // Simulate the owning markup being re-rendered/replaced: drop the whole
    // enhanced wrapper. The module's MutationObserver on #workout must invoke
    // the stored _cleanupHandler for the now-detached container.
    await page.evaluate(() => {
      const wrapper = document.getElementById('exercise')!.closest('.wpdd')!;
      wrapper.remove();
    });

    await page.waitForFunction(
      (expected) => document.querySelectorAll('.wpdd-popover').length === expected,
      basePopovers - 1,
    );

    const after = await readCounters(page);
    expect(after.winScroll - base.winScroll, 'scroll reposition listener must be removed').toBe(-1);
    expect(after.winResize - base.winResize, 'resize reposition listener must be removed').toBe(-1);
    expect(after.docClick - base.docClick, 'outside-click document listener must be removed').toBe(-1);
  });
});
