/**
 * E2E Test: Plan Volume Progress drawer
 *
 * Covers the §12.3 verification matrix from
 * docs/archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION_EXECUTION.md:
 *  - Active plan drives the drawer on /workout_plan.
 *  - Add / replace / clear / starter-plan changes refresh the panel.
 *  - Advanced mode swaps the row taxonomy.
 *  - Deactivate / delete-active degrades to an empty state.
 *  - Drawer open state persists across reloads.
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

const VOLUME_PROGRESS_ENDPOINT = '/api/volume_progress';
const DRAWER_VIEWPORTS = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'tablet', width: 768, height: 900 },
    { name: 'mobile', width: 375, height: 812 },
];
const DRAWER_THEMES = ['light', 'dark'] as const;

async function clearActivePlans(page) {
    const response = await page.request.get('/api/volume_history');
    const payload = await response.json();
    const data = payload?.data ?? {};
    for (const planId of Object.keys(data)) {
        await page.request.delete(`/api/volume_plan/${planId}`).catch(() => null);
    }
}

async function saveAndActivatePlan(page, body) {
    const response = await page.request.post('/api/save_volume_plan', {
        data: { activate: true, ...body }
    });
    expect(response.ok(), 'expected /api/save_volume_plan to succeed').toBeTruthy();
    const payload = await response.json();
    return payload?.data?.plan_id ?? payload?.plan_id;
}

async function addExerciseToPlan(page, exercise, sets, routine = 'GYM - Full Body - Workout A') {
    const response = await page.request.post('/add_exercise', {
        data: {
            routine,
            exercise,
            sets,
            min_rep_range: 6,
            max_rep_range: 10,
            rir: 2,
            rpe: 8,
            weight: 100,
        }
    });
    expect(response.ok(), `expected /add_exercise to succeed for ${exercise}`).toBeTruthy();
}

function progressResponsePromise(page) {
    return page.waitForResponse(
        (response) => response.url().includes(VOLUME_PROGRESS_ENDPOINT) && response.ok(),
        { timeout: 5000 }
    );
}

async function dispatchVolumeChange(page, reason) {
    const settled = progressResponsePromise(page);
    await page.evaluate((triggerReason) => {
        document.dispatchEvent(new CustomEvent('workout-plan:volume-affecting-change', {
            detail: { reason: triggerReason }
        }));
    }, reason);
    await settled;
}

async function getDrawerRowText(page, muscle) {
    const row = page.locator('.vp-row', { has: page.locator('.vp-row__name', { hasText: muscle }) });
    await expect(row).toBeVisible();
    return (await row.locator('.vp-row__sets').innerText()).trim();
}

async function expectDrawerLayoutStable(page, theme) {
    const drawer = page.locator('#vpDrawer');
    await expect(drawer).toHaveAttribute('aria-hidden', 'false');
    await expect(drawer.locator('.vp-row').first()).toBeVisible();
    await expect(drawer.locator('.vp-progress').first()).toBeVisible();
    await expect.poll(async () => {
        const box = await drawer.boundingBox();
        const viewport = page.viewportSize();
        if (!box || !viewport) return false;
        return box.x >= -1 && box.x + box.width <= viewport.width + 1;
    }).toBe(true);

    const layout = await page.evaluate(() => {
        const drawerEl = document.getElementById('vpDrawer');
        const rectOf = (element) => {
            const rect = element.getBoundingClientRect();
            return {
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
                left: rect.left,
                width: rect.width,
                height: rect.height,
            };
        };

        const header = drawerEl?.querySelector('.vp-drawer__header');
        const body = drawerEl?.querySelector('.vp-drawer__body');
        const firstRow = drawerEl?.querySelector('.vp-row');
        const close = drawerEl?.querySelector('.vp-close');
        const progress = drawerEl?.querySelector('.vp-progress');

        return {
            viewport: { width: window.innerWidth, height: window.innerHeight },
            theme: document.documentElement.getAttribute('data-theme'),
            drawer: drawerEl ? rectOf(drawerEl) : null,
            header: header ? rectOf(header) : null,
            body: body ? rectOf(body) : null,
            firstRow: firstRow ? rectOf(firstRow) : null,
            close: close ? rectOf(close) : null,
            progress: progress ? rectOf(progress) : null,
            drawerBackground: drawerEl ? getComputedStyle(drawerEl).backgroundColor : '',
            bodyOverflowY: body ? getComputedStyle(body).overflowY : '',
        };
    });

    expect(layout.theme).toBe(theme);
    expect(layout.drawer).not.toBeNull();
    expect(layout.header).not.toBeNull();
    expect(layout.body).not.toBeNull();
    expect(layout.firstRow).not.toBeNull();
    expect(layout.close).not.toBeNull();
    expect(layout.progress).not.toBeNull();

    const drawerBox = layout.drawer!;
    const headerBox = layout.header!;
    const bodyBox = layout.body!;
    const firstRowBox = layout.firstRow!;
    const closeBox = layout.close!;
    const progressBox = layout.progress!;

    expect(drawerBox.left).toBeGreaterThanOrEqual(-1);
    expect(drawerBox.top).toBeGreaterThanOrEqual(-1);
    expect(drawerBox.right).toBeLessThanOrEqual(layout.viewport.width + 1);
    expect(drawerBox.bottom).toBeLessThanOrEqual(layout.viewport.height + 1);
    expect(drawerBox.width).toBeLessThanOrEqual(layout.viewport.width + 1);
    expect(drawerBox.height).toBeLessThanOrEqual(layout.viewport.height + 1);

    expect(headerBox.bottom).toBeLessThanOrEqual(bodyBox.top + 1);
    expect(firstRowBox.left).toBeGreaterThanOrEqual(drawerBox.left);
    expect(firstRowBox.right).toBeLessThanOrEqual(drawerBox.right + 1);
    expect(firstRowBox.top).toBeGreaterThanOrEqual(bodyBox.top - 1);
    expect(closeBox.left).toBeGreaterThanOrEqual(drawerBox.left);
    expect(closeBox.right).toBeLessThanOrEqual(drawerBox.right + 1);
    expect(progressBox.width).toBeGreaterThan(0);
    expect(layout.bodyOverflowY).toMatch(/auto|scroll/);

    if (theme === 'dark') {
        expect(layout.drawerBackground).not.toBe('rgb(255, 255, 255)');
    }
}

test.describe('Plan volume progress drawer', () => {
    test.beforeEach(async ({ page, consoleErrors }) => {
        consoleErrors.startCollecting();
        await resetWorkoutPlan(page);
        await clearActivePlans(page);
    });

    test.afterEach(async ({ consoleErrors }) => {
        consoleErrors.assertNoErrors();
    });

    test('happy path basic: drawer reflects planned vs target after add', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 4,
            volumes: {
                Chest: { weekly_sets: 16, status: 'optimal' },
                Triceps: { weekly_sets: 10, status: 'optimal' },
            }
        });

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        const summary = page.locator('#vpActiveSummary');
        await expect(summary).toContainText(/Active plan: #\d+/);

        await page.locator('#vpToggle').click();
        await expect(page.locator('#vpDrawer')).toHaveAttribute('aria-hidden', 'false');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toContain('/ 16');

        await addExerciseToPlan(page, 'Bench Press', 3);
        await dispatchVolumeChange(page, 'e2e-add');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('3 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Triceps')).toBe('1.5 / 10');

        const clearResponse = await page.request.post('/clear_workout_plan');
        expect(clearResponse.ok(), 'expected /clear_workout_plan to succeed').toBeTruthy();
        await dispatchVolumeChange(page, 'e2e-revert');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('0 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Triceps')).toBe('0 / 10');
    });

    test('replace exercise still refreshes drawer when sets are unchanged', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 4,
            volumes: {
                Chest: { weekly_sets: 16, status: 'optimal' },
                Quadriceps: { weekly_sets: 16, status: 'optimal' },
            }
        });

        await addExerciseToPlan(page, 'Bench Press', 3);

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect(page.locator('#vpDrawer')).toHaveAttribute('aria-hidden', 'false');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('3 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Quadriceps')).toBe('0 / 16');

        // Simulate the result of an exercise replacement: same sets, different
        // primary muscle. Codex §13.8: drawer must refresh even though `sets`
        // did not change.
        const clearResponse = await page.request.post('/clear_workout_plan');
        expect(clearResponse.ok()).toBeTruthy();
        await addExerciseToPlan(page, 'Squat', 3);
        await dispatchVolumeChange(page, 'replace-exercise');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('0 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Quadriceps')).toBe('3 / 16');
    });

    test('clear plan refreshes drawer to all zeros', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 4,
            volumes: {
                Chest: { weekly_sets: 16, status: 'optimal' },
                Quadriceps: { weekly_sets: 16, status: 'optimal' },
            }
        });

        await addExerciseToPlan(page, 'Bench Press', 3);
        await addExerciseToPlan(page, 'Squat', 4);

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('3 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Quadriceps')).toBe('4 / 16');

        const clearResponse = await page.request.post('/clear_workout_plan');
        expect(clearResponse.ok()).toBeTruthy();
        await dispatchVolumeChange(page, 'clear-workout-plan');

        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('0 / 16');
        await expect.poll(async () => getDrawerRowText(page, 'Quadriceps')).toBe('0 / 16');
    });

    test('starter plan generate refreshes drawer with populated rows', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 4,
            volumes: {
                Chest: { weekly_sets: 16, status: 'optimal' },
                Quadriceps: { weekly_sets: 16, status: 'optimal' },
                Hamstrings: { weekly_sets: 12, status: 'optimal' },
                'Latissimus-Dorsi': { weekly_sets: 14, status: 'optimal' },
            }
        });

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('0 / 16');

        const generateResponse = await page.request.post('/generate_starter_plan', {
            data: {
                training_days: 2,
                environment: 'gym',
                experience_level: 'intermediate',
                goal: 'hypertrophy',
                volume_scale: 1.0,
                overwrite: true,
                persist: true,
            },
        });

        if (!generateResponse.ok()) {
            test.skip(true, `starter-plan generator unavailable in this environment: status=${generateResponse.status()}`);
            return;
        }

        await dispatchVolumeChange(page, 'starter-plan-generated');

        // Generator output is non-deterministic; assert that at least one
        // tracked muscle row left zero — proving the drawer refetched.
        await expect.poll(async () => {
            const muscles = ['Chest', 'Quadriceps', 'Hamstrings'];
            for (const muscle of muscles) {
                const text = await getDrawerRowText(page, muscle);
                const planned = Number((text.split('/')[0] ?? '0').trim());
                if (planned > 0) return true;
            }
            return false;
        }, { timeout: 5000 }).toBe(true);
    });

    test('deactivate from history collapses drawer to empty state', async ({ page }) => {
        const planId = await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 3,
            volumes: { Chest: { weekly_sets: 12, status: 'optimal' } }
        });

        await page.goto(ROUTES.VOLUME_SPLITTER);
        await waitForPageReady(page);

        const activateBtn = page.locator(`button.activate-plan[data-plan-id="${planId}"]`);
        await expect(activateBtn).toBeVisible();
        await expect(activateBtn).toHaveAttribute('data-active', 'true');
        await Promise.all([
            page.waitForResponse((response) => response.url().includes(`/api/volume_plan/${planId}/deactivate`) && response.ok()),
            activateBtn.click()
        ]);

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect(page.locator('#vpDrawer .vp-state')).toContainText(/No active volume plan/i);
        await expect(page.locator('#vpActiveSummary')).toContainText('No active plan');
    });

    test('drawer open state persists across reload', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 3,
            volumes: { Chest: { weekly_sets: 12, status: 'optimal' } }
        });

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect(page.locator('#vpDrawer')).toHaveAttribute('aria-hidden', 'false');

        await page.reload();
        await waitForPageReady(page);

        await expect(page.locator('#vpDrawer')).toHaveAttribute('aria-hidden', 'false');
    });

    test('deleting the active plan degrades gracefully', async ({ page }) => {
        const planId = await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 3,
            volumes: { Chest: { weekly_sets: 12, status: 'optimal' } }
        });

        const deleteResponse = await page.request.delete(`/api/volume_plan/${planId}`);
        expect(deleteResponse.ok()).toBeTruthy();

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        await expect(page.locator('#vpDrawer .vp-state')).toContainText(/No active volume plan/i);
    });

    test('untargeted muscles render under "Bonus from compounds", not as N / 0', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'basic',
            training_days: 4,
            volumes: {
                Chest: { weekly_sets: 16, status: 'optimal' },
            }
        });

        await addExerciseToPlan(page, 'Bench Press', 4);

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        const drawer = page.locator('#vpDrawer');
        await expect(drawer).toHaveAttribute('aria-hidden', 'false');

        const targetedList = drawer.locator('.vp-list:not(.vp-list--bonus)');
        const bonusSection = drawer.locator('.vp-bonus');
        const bonusList = drawer.locator('.vp-list--bonus');

        await expect(targetedList.locator('.vp-row__name', { hasText: 'Chest' })).toBeVisible();
        await expect.poll(async () =>
            (await targetedList.locator('.vp-row', { has: page.locator('.vp-row__name', { hasText: 'Chest' }) })
                .locator('.vp-row__sets').innerText()).trim()
        ).toBe('4 / 16');

        await expect(bonusSection).toBeVisible();
        await expect(bonusSection.locator('.vp-bonus__heading')).toHaveText('Bonus from compounds');
        await expect(bonusList.locator('.vp-row--bonus').first()).toBeVisible();

        const tricepsBonusRow = bonusList.locator('.vp-row--bonus', {
            has: page.locator('.vp-row__name', { hasText: 'Triceps' })
        });
        await expect(tricepsBonusRow).toBeVisible();
        const tricepsText = (await tricepsBonusRow.locator('.vp-row__sets').innerText()).trim();
        expect(tricepsText).toBe('2 sets');
        expect(tricepsText).not.toMatch(/\/\s*0/);

        await expect(targetedList.locator('.vp-row__name', { hasText: 'Triceps' })).toHaveCount(0);
    });

    test('§10.5: Save & Activate via UI moves keyboard focus to the active-plan summary', async ({ page }) => {
        await page.goto(ROUTES.VOLUME_SPLITTER);
        await waitForPageReady(page);

        await page.locator(SELECTORS.TRAINING_DAYS).selectOption('3');
        await page.locator('#sliders input.volume-slider[data-muscle="Chest"]').evaluate((element) => {
            const input = element as HTMLInputElement;
            input.value = '12';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        });
        await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
        await expect(page.locator('.results-section')).not.toHaveClass(/d-none/);

        const summary = page.locator('#volume-active-summary');

        await Promise.all([
            page.waitForResponse((response) =>
                response.url().includes('/api/save_volume_plan') &&
                response.request().method() === 'POST' &&
                response.ok()
            ),
            page.waitForResponse((response) =>
                response.url().includes('/api/volume_history') &&
                response.request().method() === 'GET' &&
                response.ok()
            ),
            page.locator('#save-activate-volume').click(),
        ]);

        await expect(summary).toContainText(/Active plan: #\d+/);
        await expect(summary).toBeFocused();
    });

    test('advanced mode keys drawer rows by advanced muscle names', async ({ page }) => {
        await saveAndActivatePlan(page, {
            mode: 'advanced',
            training_days: 4,
            volumes: {
                'upper-pectoralis': { weekly_sets: 8, status: 'optimal' },
                'mid-lower-pectoralis': { weekly_sets: 8, status: 'optimal' }
            }
        });

        await page.goto(ROUTES.WORKOUT_PLAN);
        await waitForPageReady(page);

        await page.locator('#vpToggle').click();
        const drawer = page.locator('#vpDrawer');
        await expect(drawer.locator('.vp-row__name', { hasText: 'upper-pectoralis' })).toBeVisible();
        await expect(drawer.locator('.vp-row__name', { hasText: 'mid-lower-pectoralis' })).toBeVisible();
    });

    for (const viewport of DRAWER_VIEWPORTS) {
        for (const theme of DRAWER_THEMES) {
            test(`viewport matrix: ${viewport.name} ${theme}`, async ({ page }) => {
                await page.setViewportSize({ width: viewport.width, height: viewport.height });
                await page.addInitScript((desiredTheme) => {
                    localStorage.setItem('darkMode', desiredTheme === 'dark' ? 'true' : 'false');
                }, theme);

                await saveAndActivatePlan(page, {
                    mode: 'basic',
                    training_days: 4,
                    volumes: {
                        Chest: { weekly_sets: 16, status: 'optimal' },
                        Triceps: { weekly_sets: 10, status: 'optimal' },
                        Quadriceps: { weekly_sets: 16, status: 'optimal' },
                    }
                });
                await addExerciseToPlan(page, 'Bench Press', 3);

                await page.goto(ROUTES.WORKOUT_PLAN);
                await waitForPageReady(page);
                await page.locator('#vpToggle').click();

                await expect.poll(async () => getDrawerRowText(page, 'Chest')).toBe('3 / 16');
                await expectDrawerLayoutStable(page, theme);
            });
        }
    }
});
