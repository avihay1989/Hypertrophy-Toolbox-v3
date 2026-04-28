import { test, expect, ROUTES, SELECTORS, waitForPageReady, resetWorkoutPlan } from './fixtures';

test.beforeEach(async ({ page }) => {
  await resetWorkoutPlan(page);
  await page.request.post('/api/user_profile', {
    data: {
      gender: null,
      age: null,
      height_cm: null,
      weight_kg: null,
      experience_years: null,
    },
  });
  await page.request.post('/api/user_profile/lifts', {
    data: [
      { lift_key: 'barbell_bicep_curl', weight_kg: null, reps: null },
      { lift_key: 'barbell_bench_press', weight_kg: null, reps: null },
    ],
  });
  await page.request.post('/api/user_profile/preferences', {
    data: { complex: 'heavy', accessory: 'moderate', isolated: 'light' },
  });
});

test.describe('User Profile', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.USER_PROFILE);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('onboarding banner is visible and collapsible', async ({ page }) => {
    const banner = page.locator('.profile-onboarding');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('About this page');
    await expect(banner).toContainText('personalises the suggestions');
    await expect(banner).toContainText('Reference Lifts');
    await expect(banner).toContainText('Rep-Range Preferences');
    await expect(banner).toContainText('starting suggestion');

    const toggle = banner.locator('.collapse-toggle');
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(banner.locator('#profile-onboarding-content')).toBeVisible();
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(banner.locator('#profile-onboarding-content')).toBeHidden();
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(banner.locator('#profile-onboarding-content')).toBeVisible();
  });

  test('section Hide buttons collapse and re-expand each profile section (Issue #3)', async ({ page }) => {
    // Issue #24 — Reference Lifts is now two side-by-side cards (anterior +
    // posterior), each with its own collapse toggle. Demographics and
    // Rep-Range Preferences keep their original single-frame layout.
    const sections: Array<{ selector: string; contentId: string; title: string }> = [
      {
        selector: '.user-profile-layout > [data-section="demographics"]',
        contentId: 'profile-demographics-content',
        title: 'Demographics',
      },
      {
        selector: '[data-section="reference lifts anterior"]',
        contentId: 'profile-lifts-content-anterior',
        title: 'Reference Lifts — Anterior',
      },
      {
        selector: '[data-section="reference lifts posterior"]',
        contentId: 'profile-lifts-content-posterior',
        title: 'Reference Lifts — Posterior',
      },
      {
        selector: '.user-profile-layout > [data-section="rep preferences"]',
        contentId: 'profile-preferences-content',
        title: 'Rep-Range Preferences',
      },
    ];

    for (const { selector, contentId, title } of sections) {
      const frame = page.locator(selector);
      await expect(frame, `frame visible: ${title}`).toBeVisible();

      const toggle = frame.locator('.collapse-toggle').first();
      const content = page.locator(`#${contentId}`);
      const text = toggle.locator('.toggle-text');

      await expect(toggle).toHaveAttribute('aria-expanded', 'true');
      await expect(toggle).toHaveAttribute('aria-controls', contentId);
      await expect(content).toBeVisible();
      await expect(text).toHaveText('Hide');

      await toggle.click();
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      await expect(content).toBeHidden();
      await expect(text).toHaveText('Show');
      await expect(frame).toHaveClass(/collapsed/);

      await toggle.click();
      await expect(toggle).toHaveAttribute('aria-expanded', 'true');
      await expect(content).toBeVisible();
      await expect(text).toHaveText('Hide');
      await expect(frame).not.toHaveClass(/collapsed/);
    }
  });

  test('section Hide buttons use Calm Glass styling tokens (Issue #3)', async ({ page }) => {
    const toggle = page
      .locator('.user-profile-layout > [data-section="demographics"] .collapse-toggle')
      .first();
    await expect(toggle).toBeVisible();

    const styles = await toggle.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        cursor: cs.cursor,
        borderRadius: cs.borderRadius,
        borderStyle: cs.borderTopStyle,
        borderWidth: cs.borderTopWidth,
        background: cs.backgroundColor || cs.backgroundImage,
      };
    });

    expect(styles.cursor).toBe('pointer');
    expect(styles.borderStyle).toBe('solid');
    expect(parseFloat(styles.borderRadius)).toBeGreaterThan(4);
    expect(parseFloat(styles.borderWidth)).toBeGreaterThan(0);
  });

  test('reference lifts explainer toggles open and shows the worked example', async ({ page }) => {
    const explainer = page.locator('.profile-explainer');
    await expect(explainer).toBeVisible();
    await expect(explainer).not.toHaveAttribute('open', '');

    const summary = explainer.locator('.profile-explainer-summary');
    await expect(summary).toContainText('How does this work?');

    await summary.click();
    await expect(explainer).toHaveAttribute('open', '');

    const body = explainer.locator('.profile-explainer-body');
    await expect(body).toBeVisible();
    await expect(body).toContainText('Epley');
    await expect(body).toContainText('1.00');
    await expect(body).toContainText('0.70');
    await expect(body).toContainText('0.40');
    await expect(body).toContainText('Heavy');
    await expect(body).toContainText('Moderate');
    await expect(body).toContainText('Light');
    await expect(body).toContainText('63');
    await expect(body).toContainText('Barbell Back Squat');
  });

  test('gender select shows Male/Female labels and no Other option (Issue #2)', async ({ page }) => {
    const select = page.locator('#profile-gender');
    const options = select.locator('option:not([value=""])');
    await expect(options).toHaveCount(2);

    const male = select.locator('option[value="M"]');
    await expect(male).toHaveCount(1);
    await expect(male).toHaveText('Male');

    const female = select.locator('option[value="F"]');
    await expect(female).toHaveCount(1);
    await expect(female).toHaveText('Female');

    await expect(select.locator('option[value="Other"]')).toHaveCount(0);
  });

  test('layout renders Demographics + Preferences row above full-width Reference Lifts at desktop width (Issue #24)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    const demographics = page.locator('.user-profile-layout > [data-section="demographics"]');
    const referenceLifts = page.locator('.user-profile-layout > [data-section="reference lifts"]');
    const preferences = page.locator('.user-profile-layout > [data-section="rep preferences"]');

    const [demoBox, refBox, prefBox] = await Promise.all([
      demographics.boundingBox(),
      referenceLifts.boundingBox(),
      preferences.boundingBox(),
    ]);
    if (!demoBox || !refBox || !prefBox) {
      throw new Error('Expected all profile sections to render with a bounding box');
    }

    // Issue #24 follow-up: Demographics + Rep-Range Preferences share row 1
    // (mirroring the overview grid above), Reference Lifts spans row 2 at
    // the full page width. The two upper cards share roughly the same top
    // edge with Demographics on the left.
    expect(Math.abs(demoBox.y - prefBox.y)).toBeLessThan(8);
    expect(demoBox.x).toBeLessThan(prefBox.x);

    // Reference Lifts sits below both upper cards.
    expect(refBox.y).toBeGreaterThan(demoBox.y + demoBox.height - 4);
    expect(refBox.y).toBeGreaterThan(prefBox.y + prefBox.height - 4);

    // Reference Lifts spans the full layout width — wider than the sum of
    // the two upper cards minus the inter-column gap.
    expect(refBox.width).toBeGreaterThan(demoBox.width + prefBox.width - 32);
  });

  test('layout collapses to single column on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 600, height: 900 });

    const demographics = page.locator('.user-profile-layout > [data-section="demographics"]');
    const referenceLifts = page.locator('.user-profile-layout > [data-section="reference lifts"]');
    const preferences = page.locator('.user-profile-layout > [data-section="rep preferences"]');

    const [demoBox, refBox, prefBox] = await Promise.all([
      demographics.boundingBox(),
      referenceLifts.boundingBox(),
      preferences.boundingBox(),
    ]);
    if (!demoBox || !refBox || !prefBox) {
      throw new Error('Expected all profile sections to render with a bounding box');
    }

    // Stacked vertically: Reference Lifts below Demographics, Preferences below Reference Lifts.
    expect(refBox.y).toBeGreaterThan(demoBox.y + demoBox.height - 4);
    expect(prefBox.y).toBeGreaterThan(refBox.y + refBox.height - 4);
  });

  test('reference lifts split into anterior and posterior cards at desktop width (Issue #24)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    // Both side-by-side cards must render with the standard data-section
    // hooks the route + bodymap rely on.
    const anteriorCard = page.locator('[data-section="reference lifts anterior"]');
    const posteriorCard = page.locator('[data-section="reference lifts posterior"]');
    await expect(anteriorCard).toBeVisible();
    await expect(posteriorCard).toBeVisible();

    const [anteriorBox, posteriorBox] = await Promise.all([
      anteriorCard.boundingBox(),
      posteriorCard.boundingBox(),
    ]);
    if (!anteriorBox || !posteriorBox) {
      throw new Error('Expected both Reference Lifts cards to render with a bounding box');
    }
    // Side-by-side at ≥1200px: shared top edge, anterior left of posterior.
    expect(Math.abs(anteriorBox.y - posteriorBox.y)).toBeLessThan(8);
    expect(anteriorBox.x).toBeLessThan(posteriorBox.x);

    // Chest sits on the anterior card; Hamstrings sits on the posterior card.
    const chestRow = anteriorCard.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    const hamstringRow = posteriorCard.locator('.reference-lift-row[data-lift-key="romanian_deadlift"]');
    await expect(chestRow).toBeVisible();
    await expect(hamstringRow).toBeVisible();
    await expect(chestRow).toHaveAttribute('data-side', 'anterior');
    await expect(hamstringRow).toHaveAttribute('data-side', 'posterior');

    // Filling a chest reference lift inside the anterior card flips the
    // Coverage map's chest entry to `state-measured` (Issue #19 live update
    // still wires through after the partition lands).
    await chestRow.locator('[name="weight_kg"]').fill('100');
    await chestRow.locator('[name="reps"]').fill('5');
    const chestPolygon = page
      .locator('.profile-bodymap .muscle-region[data-bodymap-muscle="Chest"]')
      .first();
    await expect(chestPolygon).toHaveClass(/state-measured/, { timeout: 4000 });
  });

  test('reference-lift rows stack vertically inside each card at desktop width (Issue #24)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    // Issue #15's inner 2-column row layout is intentionally reverted — the
    // ~290 px-wide side cards are too narrow for the existing label/weight/
    // reps row template. Rows must therefore stack vertically inside each
    // card (next row sits below the previous row, not next to it).
    const chestSlugs = [
      'barbell_bench_press',
      'dumbbell_bench_press',
      'incline_bench_press',
    ];
    const [row0, row1, row2] = await Promise.all(
      chestSlugs.map(slug =>
        page
          .locator(`.reference-lift-row[data-lift-key="${slug}"]`)
          .boundingBox()
      )
    );
    if (!row0 || !row1 || !row2) {
      throw new Error('Expected the first three Chest reference-lift rows to render');
    }
    // Each row drops below the previous one, all sharing roughly the same
    // left edge (single column inside the card).
    expect(row1.y).toBeGreaterThan(row0.y + row0.height - 4);
    expect(row2.y).toBeGreaterThan(row1.y + row1.height - 4);
    expect(Math.abs(row0.x - row1.x)).toBeLessThan(8);
    expect(Math.abs(row0.x - row2.x)).toBeLessThan(8);
  });

  test('reference lifts cards stack at tablet width (Issue #24)', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 900 });

    const anteriorCard = page.locator('[data-section="reference lifts anterior"]');
    const posteriorCard = page.locator('[data-section="reference lifts posterior"]');

    const [anteriorBox, posteriorBox] = await Promise.all([
      anteriorCard.boundingBox(),
      posteriorCard.boundingBox(),
    ]);
    if (!anteriorBox || !posteriorBox) {
      throw new Error('Expected both Reference Lifts cards to render with a bounding box');
    }
    // Below 1200 px the cards stack vertically — Anterior on top, Posterior
    // below. They should share roughly the same left edge.
    expect(posteriorBox.y).toBeGreaterThan(anteriorBox.y + anteriorBox.height - 4);
    expect(Math.abs(anteriorBox.x - posteriorBox.x)).toBeLessThan(8);
  });

  test('reference lifts cards stack on mobile (Issue #24)', async ({ page }) => {
    await page.setViewportSize({ width: 600, height: 900 });

    const anteriorCard = page.locator('[data-section="reference lifts anterior"]');
    const posteriorCard = page.locator('[data-section="reference lifts posterior"]');

    const [anteriorBox, posteriorBox] = await Promise.all([
      anteriorCard.boundingBox(),
      posteriorCard.boundingBox(),
    ]);
    if (!anteriorBox || !posteriorBox) {
      throw new Error('Expected both Reference Lifts cards to render with a bounding box');
    }
    // Mobile: cards stack identically to tablet, no horizontal overflow.
    expect(posteriorBox.y).toBeGreaterThan(anteriorBox.y + anteriorBox.height - 4);
  });

  test('reference lifts stack one-per-row on mobile inside the card', async ({ page }) => {
    await page.setViewportSize({ width: 600, height: 900 });

    const chestSlugs = ['barbell_bench_press', 'dumbbell_bench_press'];
    const [row0, row1] = await Promise.all(
      chestSlugs.map(slug =>
        page
          .locator(`.reference-lift-row[data-lift-key="${slug}"]`)
          .boundingBox()
      )
    );
    if (!row0 || !row1) {
      throw new Error('Expected the first two Chest reference-lift rows to render');
    }
    // Mobile single-column: row 1 sits below row 0, not next to it.
    expect(row1.y).toBeGreaterThan(row0.y + row0.height - 4);
  });

  test('per-hand hint is visible only next to dumbbell reference-lift rows', async ({ page }) => {
    // Issue #10: dumbbell weights are entered per hand (one dumbbell).
    // The questionnaire surfaces a "(per hand)" hint inline next to the
    // Weight label on every dumbbell-equipped lift, and nowhere else.
    // The fuller "Per hand — one dumbbell" description lives in the
    // hint's title attribute (hover tooltip).
    const dumbbellRow = page.locator(
      '.reference-lift-row[data-lift-key="dumbbell_bench_press"]'
    );
    const dumbbellHint = dumbbellRow.locator('.reference-lift-hand-hint');
    await expect(dumbbellRow).toHaveAttribute('data-dumbbell', 'true');
    await expect(dumbbellHint).toBeVisible();
    await expect(dumbbellHint).toContainText('per hand');
    await expect(dumbbellHint).toHaveAttribute('title', /one dumbbell/);

    // Sanity-check a second dumbbell row (lateral raise) — same hint.
    const lateralRow = page.locator(
      '.reference-lift-row[data-lift-key="dumbbell_lateral_raise"]'
    );
    await expect(lateralRow.locator('.reference-lift-hand-hint')).toBeVisible();

    // Non-dumbbell rows must NOT carry the hint or the data flag.
    const barbellRow = page.locator(
      '.reference-lift-row[data-lift-key="barbell_bench_press"]'
    );
    await expect(barbellRow).not.toHaveAttribute('data-dumbbell', 'true');
    await expect(barbellRow.locator('.reference-lift-hand-hint')).toHaveCount(0);
  });

  test('reference lifts questionnaire renders new Calves / Glutes-Hips / Lower-Back rows under the correct muscle headings (Issue #20)', async ({ page }) => {
    // Each row carries its own data-lift-key + sits inside a group whose
    // first sibling is the muscle-group <h4>. Asserting (a) the row exists
    // and (b) the nearest preceding heading text matches the expected
    // group catches mis-grouped slugs (e.g. a glute compound that ends
    // up under Lower Back) without depending on exact pixel positions.
    const expectations: Array<{ slug: string; group: RegExp }> = [
      // Calves expansion.
      { slug: 'seated_calf_raise', group: /^Calves$/ },
      { slug: 'leg_press_calf_raise', group: /^Calves$/ },
      { slug: 'smith_machine_calf_raise', group: /^Calves$/ },
      { slug: 'single_leg_standing_calf_raise', group: /^Calves$/ },
      { slug: 'donkey_calf_raise', group: /^Calves$/ },
      // Issue #24 — "Legs — Quads & Glutes" → "Quads" (anterior),
      // "Legs — Hamstrings" → "Hamstrings". Glute-dominant compounds +
      // isolations live under "Glutes / Hip" alongside `machine_hip_abduction`
      // (now joined by `hip_thrust`, which moved out of the legacy quads
      // group). Bilateral leg compounds (Bulgarian split squat, reverse
      // lunge) stay anterior under "Quads". Sumo deadlift + seated good
      // morning stay posterior under "Hamstrings".
      { slug: 'barbell_glute_bridge', group: /^Glutes \/ Hip$/ },
      { slug: 'cable_pull_through', group: /^Glutes \/ Hip$/ },
      { slug: 'b_stance_hip_thrust', group: /^Glutes \/ Hip$/ },
      { slug: 'cable_kickback', group: /^Glutes \/ Hip$/ },
      { slug: 'hip_thrust', group: /^Glutes \/ Hip$/ },
      { slug: 'bulgarian_split_squat', group: /^Quads$/ },
      { slug: 'reverse_lunge', group: /^Quads$/ },
      { slug: 'sumo_deadlift', group: /^Hamstrings$/ },
      { slug: 'seated_good_morning', group: /^Hamstrings$/ },
      // Lower back expansion.
      { slug: 'loaded_back_extension', group: /^Lower Back$/ },
      { slug: 'reverse_hyperextension', group: /^Lower Back$/ },
      { slug: 'jefferson_curl', group: /^Lower Back$/ },
    ];

    for (const { slug, group } of expectations) {
      const row = page.locator(`.reference-lift-row[data-lift-key="${slug}"]`);
      await expect(row, `row visible: ${slug}`).toBeVisible();

      const groupHeading = await row.evaluate((el) => {
        // Walk previous siblings up to the closest .reference-lift-group-title.
        let cursor: Element | null = el.previousElementSibling;
        while (cursor) {
          if (cursor.classList.contains('reference-lift-group-title')) {
            return cursor.textContent?.trim() ?? '';
          }
          cursor = cursor.previousElementSibling;
        }
        return '';
      });
      expect(groupHeading, `group heading for ${slug}`).toMatch(group);
    }
  });

  test('Profile nav link gets active highlight on /user_profile and loses it on navigation away (Issue #12)', async ({ page }) => {
    const profileNav = page.locator(SELECTORS.NAV_USER_PROFILE);
    await expect(profileNav).toBeVisible();
    await expect(profileNav).toHaveClass(/\bactive\b/);

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    await expect(page.locator(SELECTORS.NAV_USER_PROFILE)).not.toHaveClass(/\bactive\b/);
    await expect(page.locator(SELECTORS.NAV_WORKOUT_PLAN)).toHaveClass(/\bactive\b/);
  });

  test('profile page saves each section without reloading', async ({ page }) => {
    await expect(page.locator(SELECTORS.PAGE_USER_PROFILE)).toBeVisible();
    await expect(page.locator(SELECTORS.NAV_USER_PROFILE)).toBeVisible();

    const demographicsPill = page.locator('#profile-demographics-form [data-autosave-status]');
    const liftsPill = page.locator('#profile-lifts-form [data-autosave-status]');
    const preferencesPill = page.locator('#profile-preferences-form [data-autosave-status]');

    await page.locator('#profile-gender').selectOption('M');
    await page.locator('#profile-age').fill('30');
    await page.locator('#profile-height').fill('180');
    await page.locator('#profile-weight').fill('80');
    await page.locator('#profile-experience').fill('5');
    await expect(demographicsPill).toHaveAttribute('data-autosave-status', 'saved', { timeout: 5000 });

    const benchRow = page.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    await benchRow.locator('[name="weight_kg"]').fill('100');
    await benchRow.locator('[name="reps"]').fill('5');
    await expect(liftsPill).toHaveAttribute('data-autosave-status', 'saved', { timeout: 5000 });

    await page.locator('label.segmented-option:has(input[name="complex"][value="moderate"])').click();
    await expect(preferencesPill).toHaveAttribute('data-autosave-status', 'saved', { timeout: 5000 });

    await page.reload();
    await waitForPageReady(page);
    await expect(page.locator('#profile-age')).toHaveValue('30');
    await expect(benchRow.locator('[name="weight_kg"]')).toHaveValue('100.0');
    await expect(page.locator('input[name="complex"][value="moderate"]')).toBeChecked();
  });

  test('"How the system sees you" card renders cold-start anchors and updates as the user fills demographics + reference lifts (Issue #17)', async ({ page }) => {
    // The file-level beforeEach only nulls bench + bicep curl. Some other
    // tests in this suite POST `preacher_curl` to the API as part of their
    // setup; null every high-impact slug here to guarantee a clean band.
    await page.request.post('/api/user_profile/lifts', {
      data: [
        'barbell_bench_press', 'barbell_back_squat', 'romanian_deadlift',
        'weighted_pullups', 'military_press', 'barbell_bicep_curl',
        'triceps_extension', 'barbell_row', 'standing_calf_raise',
        'preacher_curl',
      ].map(lift_key => ({ lift_key, weight_kg: null, reps: null })),
    });
    await page.reload();
    await waitForPageReady(page);

    const card = page.locator('[data-section="profile insights"]');
    await expect(card).toBeVisible();
    await expect(card).toContainText('How the system sees you');

    // Empty profile → population_only band, stats tiles flag the empty fields.
    // (Issue #18 replaced the classification line with stats tiles.)
    await expect(card.locator('[data-band-pill]')).toHaveText(/Population estimate only/);
    await expect(card.locator('[data-insights-tile="bodyweight"][data-empty="true"]')).toBeVisible();
    await expect(card.locator('[data-insights-tile="experience"][data-empty="true"]')).toBeVisible();
    // Anchors hidden until demographics are complete.
    await expect(card.locator('[data-insights-anchors]')).toBeHidden();

    // Fill demographics — cold-start anchors should appear with non-empty values.
    await page.locator('#profile-gender').selectOption('M');
    await page.locator('#profile-weight').fill('75');
    await page.locator('#profile-experience').fill('3');
    await expect(card.locator('[data-insights-anchors]')).toBeVisible();
    const anchorList = card.locator('[data-anchor-list]');
    // At least Bench / Squat / Deadlift / OHP anchors render with a 1RM number.
    await expect(anchorList.locator('li[data-anchor-slug="barbell_bench_press"]')).toContainText('kg 1RM');
    await expect(anchorList.locator('li[data-anchor-slug="barbell_back_squat"]')).toContainText('kg 1RM');
    await expect(anchorList.locator('li[data-anchor-slug="romanian_deadlift"]')).toContainText('kg 1RM');
    await expect(anchorList.locator('li[data-anchor-slug="military_press"]')).toContainText('kg 1RM');

    // Save the bench reference — band advances to "partial" + Replaced list shows bench.
    const benchRow = page.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    await benchRow.locator('[name="weight_kg"]').fill('100');
    await benchRow.locator('[name="reps"]').fill('5');
    await expect(card.locator('[data-band-pill]')).toHaveText(/Partially personalised/);
    await expect(card.locator('[data-insights-replaced]')).toBeVisible();
    await expect(
      card.locator('[data-replaced-list] li[data-replaced-slug="barbell_bench_press"]')
    ).toContainText('Barbell Bench Press');
    // The bench shouldn't appear in next-high-impact list anymore.
    await expect(
      card.locator('[data-missing-list] li[data-missing-slug="barbell_bench_press"]')
    ).toHaveCount(0);
  });

  test('Accuracy band advances from population-only to mostly-personalised after saving 5+ reference lifts (Issue #17)', async ({ page }) => {
    await page.request.post('/api/user_profile/lifts', {
      data: [
        'barbell_bench_press', 'barbell_back_squat', 'romanian_deadlift',
        'weighted_pullups', 'military_press', 'barbell_bicep_curl',
        'triceps_extension', 'barbell_row', 'standing_calf_raise',
        'preacher_curl',
      ].map(lift_key => ({ lift_key, weight_kg: null, reps: null })),
    });
    await page.reload();
    await waitForPageReady(page);

    const card = page.locator('[data-section="profile insights"]');
    await expect(card.locator('[data-band-pill]')).toHaveText(/Population estimate only/);

    const fillRow = async (slug: string, weight: string, reps: string) => {
      const row = page.locator(`.reference-lift-row[data-lift-key="${slug}"]`);
      await row.locator('[name="weight_kg"]').fill(weight);
      await row.locator('[name="reps"]').fill(reps);
    };

    // Cover the six major muscle groups (Chest, Back, Legs, Shoulders, Biceps, Triceps).
    await fillRow('barbell_bench_press', '100', '5');
    await fillRow('barbell_row', '80', '5');
    await fillRow('barbell_back_squat', '130', '5');
    await fillRow('military_press', '60', '5');
    await fillRow('barbell_bicep_curl', '40', '6');
    await fillRow('triceps_extension', '30', '8');

    await expect(card.locator('[data-band-pill]')).toHaveText(/Mostly personalised/);
    await expect(card.locator('[data-band-count]')).toContainText('6');
  });

  test('demographics-only profile seeds a non-zero cold-start estimate on the Plan page (Issue #16)', async ({ page }) => {
    await page.request.post('/api/user_profile', {
      data: {
        gender: 'M',
        age: 30,
        height_cm: 180,
        weight_kg: 75,
        experience_years: 3,
      },
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

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

    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('Barbell Bench Press');

    // 75 kg M intermediate (3 yrs) × Chest male ratio 1.00 × intermediate
    // multiplier 1.0 × tier 1.0 × Light pct 0.65 ≈ 48.75 (barbell complex
    // increment 1.25). The forced Light preset gives 10–15 reps / RIR 2 /
    // RPE 7.5 regardless of complex tier so the seeded suggestion errs
    // toward under-prescription.
    await expect(page.locator('#weight')).toHaveValue('48.75');
    await expect(page.locator('#min_rep')).toHaveValue('10');
    await expect(page.locator('#max_rep_range')).toHaveValue('15');
    await expect(page.locator('#rir')).toHaveValue('2');
    await expect(page.locator('#rpe')).toHaveValue('7.5');
    await expect(page.locator('#workout-estimate-provenance')).toHaveText(
      'from population estimate',
    );
  });

  test('workout plan applies profile estimate and preserves it after add', async ({ page }) => {
    await page.request.post('/api/user_profile/lifts', {
      data: [{ lift_key: 'preacher_curl', weight_kg: 35, reps: 8 }],
    });

    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

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

    let estimateRequests = 0;
    page.on('request', request => {
      if (request.url().includes('/api/user_profile/estimate')) {
        estimateRequests += 1;
      }
    });

    await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption('EZ Bar Preacher Curl');

    // Issue #14: iso→iso direct match no longer double-discounts. Epley(35,8)
    // ≈ 44.33 × 1.00 (iso/iso) × 0.65 (light) ≈ 28.82 → barbell isolated
    // rounding → 28.75 (was 11.25 pre-fix).
    await expect(page.locator('#weight')).toHaveValue('28.75');
    await expect(page.locator('#sets')).toHaveValue('3');
    await expect(page.locator('#min_rep')).toHaveValue('10');
    await expect(page.locator('#max_rep_range')).toHaveValue('15');
    await expect(page.locator('#rir')).toHaveValue('2');
    await expect(page.locator('#rpe')).toHaveValue('7.5');
    await expect(page.locator('#workout-estimate-provenance')).toHaveText('from your profile');
    expect(estimateRequests).toBe(1);

    const postAddEstimate = page.waitForResponse(response =>
      response.url().includes('/api/user_profile/estimate') && response.status() === 200
    );
    await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
    await postAddEstimate;
    await expect(page.locator(SELECTORS.TOAST_BODY)).toContainText(/added|already/i);

    await expect(page.locator('#weight')).toHaveValue('28.75');
    await expect(page.locator('#sets')).toHaveValue('3');
    await expect(page.locator('#min_rep')).toHaveValue('10');
    await expect(page.locator('#max_rep_range')).toHaveValue('15');
    await expect(page.locator('#rir')).toHaveValue('2');
    await expect(page.locator('#rpe')).toHaveValue('7.5');
    await expect(page.locator('#workout-estimate-provenance')).toHaveText('from your profile');
  });

  test('coverage map renders, flips Chest to measured after saving bench, and scrolls on click (Issue #19)', async ({ page }) => {
    await page.request.post('/api/user_profile/lifts', {
      data: [
        'barbell_bench_press', 'barbell_back_squat', 'romanian_deadlift',
        'weighted_pullups', 'military_press', 'barbell_bicep_curl',
        'triceps_extension', 'preacher_curl',
      ].map(lift_key => ({ lift_key, weight_kg: null, reps: null })),
    });
    await page.reload();
    await waitForPageReady(page);

    const card = page.locator('[data-section="muscle coverage"]');
    await expect(card).toBeVisible();
    await expect(card).toContainText('Coverage map');

    // (a) Anterior diagram renders with all coverage muscles in the
    //     cold-start outline state on first visit.
    const frontPane = card.locator('[data-bodymap-pane="front"]');
    await expect(frontPane).toBeVisible();
    // Polygons exist and got the data-bodymap-muscle attribute.
    const chestRegions = frontPane.locator('.muscle-region[data-bodymap-muscle="Chest"]');
    await expect(chestRegions.first()).toBeVisible();
    await expect(chestRegions.first()).toHaveClass(/state-cold_start_only/);

    // SR summary mirrors the same state.
    await expect(card.locator('[data-sr-muscle="Chest"]')).toHaveAttribute(
      'data-sr-state',
      'cold_start_only',
    );

    // (b) Filling Barbell Bench Press flips the Chest polygon to measured.
    const benchRow = page.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    await benchRow.locator('[name="weight_kg"]').fill('100');
    await benchRow.locator('[name="reps"]').fill('5');
    await expect(chestRegions.first()).toHaveClass(/state-measured/);
    await expect(card.locator('[data-sr-muscle="Chest"]')).toHaveAttribute(
      'data-sr-state',
      'measured',
    );

    // (c) Hover popover lists the saved lift.
    // Issue #24: scroll the page back to the top so the bodymap polygon
    // sits clear of the 64 px sticky navbar (the half-width Coverage-map
    // card renders the chest region at ~48 × 42 px, small enough that the
    // navbar overlay intercepts a hover whose scrollIntoView lands the
    // polygon at the viewport top after Playwright scrolled down to fill
    // the bench row in the form below). `force: true` then skips the
    // actionability re-check while the popover-driven flex reflow inside
    // `.profile-bodymap-stage` settles.
    await page.evaluate(() => window.scrollTo(0, 0));
    await chestRegions.first().hover({ force: true });
    const popover = card.locator('[data-bodymap-popover]');
    await expect(popover).toBeVisible();
    await expect(popover).toContainText('Barbell Bench Press');
    await expect(popover.locator('[data-popover-state]')).toHaveText('Measured');

    // (d) Clicking a cold-start polygon scrolls its improvement-lift row
    //     into view. Calves only has standing_calf_raise — clicking it
    //     should focus that input. Dispatch the click event directly via
    //     the DOM rather than going through Playwright's pointer click —
    //     `force: true` would fire at the SVG polygon's rectangular
    //     bounding box centre, which can fall outside the polygon's
    //     actual path (so the SVG receives the click and the polygon's
    //     handler never runs); a synthetic `click` on the polygon
    //     element invokes the same listener that a real user click on
    //     the polygon would.
    const calvesRegion = frontPane.locator('.muscle-region[data-bodymap-muscle="Calves"]').first();
    await calvesRegion.evaluate(el => el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })));
    await expect(
      page.locator('#lift-standing_calf_raise-weight')
    ).toBeFocused();

    // Side toggle: clicking "Back" hides the front pane and reveals back.
    await card.locator('[data-bodymap-side="back"]').click();
    await expect(frontPane).toBeHidden();
    await expect(card.locator('[data-bodymap-pane="back"]')).toBeVisible();
    await expect(card.locator('[data-bodymap-side="back"]')).toHaveClass(/is-active/);
  });

  test('"How the system sees you" card surfaces stats tiles, cohort bar, and donut after demographics + lift (Issue #18)', async ({ page }) => {
    await page.request.post('/api/user_profile/lifts', {
      data: [
        'barbell_bench_press', 'barbell_back_squat', 'romanian_deadlift',
        'weighted_pullups', 'military_press', 'barbell_bicep_curl',
        'triceps_extension', 'preacher_curl',
      ].map(lift_key => ({ lift_key, weight_kg: null, reps: null })),
    });
    await page.reload();
    await waitForPageReady(page);

    const card = page.locator('[data-section="profile insights"]');
    await expect(card).toBeVisible();

    // (a) The four stats tiles always render — even with no demographics.
    for (const key of ['bodyweight', 'height', 'age', 'experience']) {
      await expect(card.locator(`[data-insights-tile="${key}"]`)).toBeVisible();
    }
    // Empty state: tiles carry the data-empty marker the CSS keys off of.
    await expect(card.locator('[data-insights-tile="bodyweight"][data-empty="true"]')).toBeVisible();
    await expect(card.locator('[data-insights-tile="experience"][data-empty="true"]')).toBeVisible();
    // Height + age are flagged unused regardless of fill state.
    await expect(card.locator('[data-insights-tile="height"][data-unused="true"]')).toBeVisible();
    await expect(card.locator('[data-insights-tile="age"][data-unused="true"]')).toBeVisible();

    // Cohort summary shows a "fill these to calibrate" hint when empty.
    await expect(card.locator('[data-cohort-summary]')).toContainText(/fill these to calibrate/);

    // Cohort bars hidden until a canonical compound is filled.
    await expect(card.locator('[data-insights-bars]')).toBeHidden();

    // Fill demographics — tiles populate, summary recalibrates.
    await page.locator('#profile-gender').selectOption('M');
    await page.locator('#profile-weight').fill('75');
    await page.locator('#profile-experience').fill('3');
    await page.locator('#profile-age').fill('34');
    await page.locator('#profile-height').fill('178');

    await expect(card.locator('[data-insights-tile="bodyweight"] [data-tile-value]')).toContainText('75 kg');
    await expect(card.locator('[data-insights-tile="bodyweight"] [data-tile-cohort]')).toContainText(/Cohort: 70/);
    await expect(card.locator('[data-insights-tile="experience"] [data-tile-value]')).toContainText('Intermediate');
    await expect(card.locator('[data-insights-tile="experience"] [data-tile-cohort]')).toContainText(/×1.00/);
    await expect(card.locator('[data-insights-tile="height"] [data-tile-value]')).toContainText('178');
    await expect(card.locator('[data-insights-tile="age"] [data-tile-value]')).toContainText('34');
    await expect(card.locator('[data-cohort-summary]')).toContainText(/Suggestions are calibrated/);

    // (b) Saving one canonical compound reveals a cohort bar row.
    const benchRow = page.locator('.reference-lift-row[data-lift-key="barbell_bench_press"]');
    await benchRow.locator('[name="weight_kg"]').fill('100');
    await benchRow.locator('[name="reps"]').fill('5');

    await expect(card.locator('[data-insights-bars]')).toBeVisible();
    const benchBar = card.locator('[data-bar-list] [data-bar-slug="barbell_bench_press"]');
    await expect(benchBar).toBeVisible();
    await expect(benchBar).toContainText('Barbell Bench Press');
    // Epley(100, 5) ≈ 116.7 kg.
    await expect(benchBar).toContainText(/116\.7/);
    // Cold-start anchor 75 × Chest male 1.0 × intermediate 1.0 = 75 kg.
    await expect(benchBar).toContainText(/cold-start ≈ 75/);
    // Cohort upper at the next tier: 75 × (1.2 / 1.0) = 90 kg.
    await expect(benchBar).toContainText(/cohort upper ≈ 90/);

    // (c) Donut count matches the accuracy band count.
    await expect(card.locator('[data-band-count]')).toContainText(/^1 \//);
    await expect(card.locator('[data-donut-count]')).toContainText(/^1\b/);
  });
});
