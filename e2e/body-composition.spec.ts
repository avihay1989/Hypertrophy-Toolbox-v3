import { test, expect, waitForPageReady, expectToast } from './fixtures';

const PROFILE_DEMOGRAPHICS = {
    gender: 'M',
    age: 30,
    height_cm: 180,
    weight_kg: 80,
    experience_years: 5,
};

async function setDemographics(
    request: import('@playwright/test').APIRequestContext,
    payload: Record<string, unknown> | null,
) {
    await request.post('/api/user_profile', {
        data: payload ?? {
            gender: null,
            age: null,
            height_cm: null,
            weight_kg: null,
            experience_years: null,
        },
    });
}

async function deleteAllSnapshots(
    request: import('@playwright/test').APIRequestContext,
) {
    const response = await request.get('/api/body_composition/snapshots', {
        headers: { Accept: 'application/json' },
    });
    if (!response.ok()) return;
    const body = await response.json();
    for (const row of body.data ?? []) {
        await request.delete(`/api/body_composition/snapshots/${row.id}`);
    }
}

test.describe('Body Composition page', () => {
    test.beforeEach(async ({ page, consoleErrors, request }) => {
        consoleErrors.startCollecting();
        await deleteAllSnapshots(request);
    });

    test.afterEach(async ({ consoleErrors }) => {
        consoleErrors.assertNoErrors();
    });

    test('renders demographics-required empty state when profile is blank', async ({
        page,
        request,
    }) => {
        await setDemographics(request, null);
        await page.goto('/body_composition');
        await waitForPageReady(page);

        const emptyState = page.locator(
            '[data-testid="body-composition-demographics-required"]',
        );
        await expect(emptyState).toBeVisible();
        await expect(emptyState.locator('a[href="/user_profile#demographics"]')).toBeVisible();

        await expect(
            page.locator('[data-testid="body-composition-calculator"]'),
        ).toHaveCount(0);
    });

    test('live result panel computes BFP/FM/LM from tape inputs', async ({
        page,
        request,
    }) => {
        await setDemographics(request, PROFILE_DEMOGRAPHICS);
        await page.goto('/body_composition');
        await waitForPageReady(page);

        // Initial render: BMI fallback should display since tape is blank.
        const bfpEl = page.locator('[data-testid="body-composition-result-bfp"]');
        await expect(bfpEl).not.toHaveText('—');
        await expect(
            page.locator('[data-testid="body-composition-result-badge"]'),
        ).toContainText(/BMI/i);

        // Fill in male tape values: neck=38, waist=85.
        await page.locator('#bc-neck').fill('38');
        await page.locator('#bc-waist').fill('85');

        // Wait for the live preview to switch to Navy.
        await expect(
            page.locator('[data-testid="body-composition-result-badge"]'),
        ).toHaveText('Navy method');

        // BFP should be approximately 16.13 % per the formula.
        const bfpText = (await bfpEl.textContent()) ?? '';
        const bfpMatch = bfpText.match(/([\d.]+)/);
        expect(bfpMatch).not.toBeNull();
        const bfp = Number.parseFloat(bfpMatch![1]);
        expect(bfp).toBeGreaterThan(15);
        expect(bfp).toBeLessThan(17);

        // Fat-mass / lean-mass line populated.
        await expect(
            page.locator('[data-testid="body-composition-result-mass"]'),
        ).toContainText(/Fat mass: \d+\.\d kg/);
        await expect(
            page.locator('[data-testid="body-composition-result-mass"]'),
        ).toContainText(/Lean mass: \d+\.\d kg/);

        // ACE band SVG was populated by JS.
        await expect(
            page.locator('[data-testid="body-composition-ace-band"] rect'),
        ).toHaveCount(5);

        // Jackson & Pollock line includes the ideal value.
        await expect(
            page.locator('[data-testid="body-composition-jp-line"]'),
        ).toContainText(/Jackson & Pollock ideal/);
    });

    test('save snapshot adds a row to history and a polyline to the trend chart', async ({
        page,
        request,
    }) => {
        await setDemographics(request, PROFILE_DEMOGRAPHICS);
        await page.goto('/body_composition');
        await waitForPageReady(page);

        await page.locator('#bc-neck').fill('38');
        await page.locator('#bc-waist').fill('85');

        await page.locator('[data-testid="body-composition-save"]').click();

        await expectToast(page, /Snapshot saved/i);

        // History row appears.
        const historyRows = page.locator(
            '[data-testid="body-composition-history-body"] tr',
        );
        await expect(historyRows).toHaveCount(1);

        // Trend chart got a polyline (SVG element is present in the DOM
        // even though a single-point polyline has no visible extent).
        await expect(
            page.locator(
                '[data-testid="body-composition-trend-chart"] polyline[data-trend="line"]',
            ),
        ).toBeAttached();
    });

    test('hip field is hidden for male and visible for female', async ({
        page,
        request,
    }) => {
        await setDemographics(request, PROFILE_DEMOGRAPHICS);
        await page.goto('/body_composition');
        await waitForPageReady(page);
        await expect(
            page.locator('[data-testid="body-composition-hip-field"]'),
        ).toHaveCount(0);

        await setDemographics(request, {
            ...PROFILE_DEMOGRAPHICS,
            gender: 'F',
            height_cm: 165,
            weight_kg: 60,
        });
        await page.goto('/body_composition');
        await waitForPageReady(page);
        await expect(
            page.locator('[data-testid="body-composition-hip-field"]'),
        ).toBeVisible();
    });

    test('navbar entry highlights on /body_composition', async ({ page, request }) => {
        await setDemographics(request, PROFILE_DEMOGRAPHICS);
        await page.goto('/body_composition');
        await waitForPageReady(page);
        await expect(page.locator('#nav-body-composition')).toHaveClass(/active/);
    });
});
