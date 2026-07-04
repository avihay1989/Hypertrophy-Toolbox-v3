/**
 * E2E Test: Body Composition (Issue #21)
 *
 * Smoke + save-flow coverage for the standalone /body_composition page.
 */
import type { Page } from '@playwright/test';
import { test, expect, waitForPageReady } from './fixtures';
import parityCases from './fixtures/body-fat-parity.json';

const ROUTE = '/body_composition';

async function seedProfile(page: Page) {
  const res = await page.request.post('/api/user_profile', {
    data: {
      gender: 'M',
      age: 34,
      height_cm: 180,
      weight_kg: 80,
      experience_years: 5,
    },
  });
  expect(res.ok(), 'profile seed must succeed').toBeTruthy();
}

async function clearSnapshots(page: Page) {
  const listResp = await page.request.get('/api/body_composition/snapshots');
  if (!listResp.ok()) return;
  const payload = await listResp.json();
  const items = payload?.data ?? [];
  for (const snap of items) {
    await page.request.delete(`/api/body_composition/snapshots/${snap.id}`);
  }
}

test.describe('Body Composition page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await seedProfile(page);
    await clearSnapshots(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('navbar link routes to /body_composition', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
    const navLink = page.locator('#nav-body-composition');
    await expect(navLink).toBeVisible();
    await navLink.click();
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/body_composition/);
    await expect(page.locator('[data-page="body-composition"]')).toBeVisible();
  });

  test('renders form + empty trend with no snapshots', async ({ page }) => {
    await page.goto(ROUTE);
    await waitForPageReady(page);
    await expect(page.locator('#bc-form')).toBeVisible();
    await expect(page.locator('[data-bc-trend-empty]')).toBeVisible();
    await expect(page.locator('[data-bc-empty]')).toBeVisible();
    // ACE band segments are rendered client-side once the JS module boots.
    await expect(page.locator('.bc-band-segment').first()).toBeVisible();
  });

  test('save snapshot adds row to history and updates trend', async ({ page }) => {
    await page.goto(ROUTE);
    await waitForPageReady(page);

    await page.locator('#bc-neck').fill('38');
    await page.locator('#bc-waist').fill('85');

    // Live results should update before save.
    await expect(page.locator('[data-bc-bfp]')).not.toHaveText('—', { timeout: 5000 });
    await expect(page.locator('[data-bc-method-label]')).toHaveText('U.S. Navy method');

    await page.locator('#bc-save').click();

    const rows = page.locator('[data-bc-history-body] tr');
    await expect(rows).toHaveCount(1, { timeout: 5000 });
    await expect(page.locator('[data-bc-empty]')).toBeHidden();
    await expect(page.locator('[data-bc-trend-empty]')).toBeHidden();

    const polyline = page.locator('[data-bc-trend-line]');
    await expect(polyline).toHaveAttribute('points', /\d/);

    // Delete the row and confirm the empty state returns.
    await rows.first().locator('[data-bc-delete]').click();
    await expect(page.locator('[data-bc-history-body] tr')).toHaveCount(0, { timeout: 5000 });
    await expect(page.locator('[data-bc-empty]')).toBeVisible();
  });

  test('BMI fallback shows when tape fields are blank', async ({ page }) => {
    await page.goto(ROUTE);
    await waitForPageReady(page);
    await expect(page.locator('[data-bc-method-label]')).toHaveText('BMI method (fallback)');
    await expect(page.locator('[data-bc-bfp]')).not.toHaveText('—');
  });

  test('JS preview matches Python persisted Navy BFP within rounding', async ({ page }) => {
    await page.goto(ROUTE);
    await waitForPageReady(page);

    await page.locator('#bc-neck').fill('38');
    await page.locator('#bc-waist').fill('85');

    const previewText = await page.locator('[data-bc-bfp]').textContent();
    const previewMatch = previewText?.match(/([\d.]+)\s*%/);
    expect(previewMatch, `expected BFP preview text, got "${previewText}"`).not.toBeNull();
    const previewValue = Number(previewMatch![1]);

    await page.locator('#bc-save').click();
    await expect(page.locator('[data-bc-history-body] tr')).toHaveCount(1, { timeout: 5000 });

    const listResp = await page.request.get('/api/body_composition/snapshots');
    expect(listResp.ok()).toBeTruthy();
    const payload = await listResp.json();
    const snap = payload?.data?.[0];
    expect(snap, 'snapshot list should not be empty').toBeTruthy();
    expect(snap.bfp_navy, 'Navy BFP should be persisted').not.toBeNull();

    // JS displays bfp.toFixed(1); server stores the raw float. They must
    // round-trip to within ±0.05 % BFP — anything larger means the JS and
    // Python formulas have drifted.
    expect(Math.abs(previewValue - Number(snap.bfp_navy.toFixed(1)))).toBeLessThanOrEqual(0.05);
  });

  for (const parityCase of parityCases) {
    test(`shared JS/Python parity: ${parityCase.id}`, async ({ page }) => {
      const profileResp = await page.request.post('/api/user_profile', {
        data: {
          gender: parityCase.profile.gender,
          age: parityCase.profile.age,
          height_cm: parityCase.profile.height_cm,
          weight_kg: parityCase.profile.weight_kg,
          experience_years: 5,
        },
      });
      expect(profileResp.ok(), 'parity profile seed must succeed').toBeTruthy();

      await page.goto(ROUTE);
      await waitForPageReady(page);
      if (parityCase.tape) {
        await page.locator('#bc-neck').fill(String(parityCase.tape.neck_cm));
        await page.locator('#bc-waist').fill(String(parityCase.tape.waist_cm));
        if ('hip_cm' in parityCase.tape) {
          await page.locator('#bc-hip').fill(String(parityCase.tape.hip_cm));
        }
      }

      await expect(page.locator('[data-bc-method-label]')).toHaveText(parityCase.expected.method);
      await expect(page.locator('[data-bc-bfp]')).toHaveText(`${parityCase.expected.bfp.toFixed(1)} %`);
      await expect(page.locator('[data-bc-bmi]')).toHaveText(parityCase.expected.bmi.toFixed(1));
      await expect(page.locator('[data-bc-band-label]')).toHaveText(parityCase.expected.ace);
      await expect(page.locator('[data-bc-jp-ideal]')).toHaveText(
        `${parityCase.expected.jackson_pollock_ideal.toFixed(1)} %`,
      );
    });
  }
});
