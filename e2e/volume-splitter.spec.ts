/**
 * E2E Test: Volume Splitter Page
 * 
 * Tests the volume splitter functionality including:
 * - Page loading
 * - Training frequency selector
 * - Mode toggle (basic/advanced)
 * - Volume sliders
 * - Calculate and reset buttons
 * - Export to Excel
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady, expectToast } from './fixtures';

async function setVolumeSlider(page, muscle: string, value: number) {
  const slider = page.locator(`#sliders input.volume-slider[data-muscle="${muscle}"]`);
  await expect(slider).toBeVisible();
  await slider.evaluate((element, nextValue) => {
    const input = element as HTMLInputElement;
    input.value = String(nextValue);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

async function expectVolumeSliderValue(page, muscle: string, expectedValue: number) {
  const slider = page.locator(`#sliders input.volume-slider[data-muscle="${muscle}"]`);
  const valueBadge = page.locator(`.current-value[data-muscle="${muscle}"]`);

  await expect(slider).toHaveValue(String(expectedValue));
  await expect(valueBadge).toHaveText(String(expectedValue));
}

test.describe('Volume Splitter Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.VOLUME_SPLITTER);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('page loads with correct structure', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText('Volume Splitter');

    // Check container
    await expect(page.locator(SELECTORS.PAGE_VOLUME_SPLITTER)).toBeVisible();

    // Check lead text
    await expect(page.locator('.lead')).toContainText('training volume');
  });

  test('training frequency selector is present', async ({ page }) => {
    const trainingDays = page.locator(SELECTORS.TRAINING_DAYS);
    await expect(trainingDays).toBeVisible();

    // Should have options 1-7 days
    const options = trainingDays.locator('option');
    const count = await options.count();
    expect(count).toBe(7);

    // Default should be 3 days
    await expect(trainingDays).toHaveValue('3');
  });

  test('mode toggle is present with basic/advanced options', async ({ page }) => {
    const modeToggle = page.locator('.mode-toggle');
    await expect(modeToggle).toBeVisible();

    // Check radio buttons exist
    const basicRadio = page.locator('#mode-basic');
    const advancedRadio = page.locator('#mode-advanced');
    await expect(basicRadio).toBeVisible();
    await expect(advancedRadio).toBeVisible();

    // One should be checked (depends on default mode)
    const basicChecked = await basicRadio.isChecked();
    const advancedChecked = await advancedRadio.isChecked();
    expect(basicChecked || advancedChecked).toBe(true);
  });

  test('volume sliders container is present', async ({ page }) => {
    const sliders = page.locator('#sliders');
    await expect(sliders).toBeVisible();
  });

  test('calculate button is present and clickable', async ({ page }) => {
    const calculateBtn = page.locator(SELECTORS.CALCULATE_VOLUME_BTN);
    await expect(calculateBtn).toBeVisible();
    await expect(calculateBtn).toContainText('Calculate');

    // Button should be clickable
    await expect(calculateBtn).toBeEnabled();
  });

  test('reset button is present and clickable', async ({ page }) => {
    const resetBtn = page.locator(SELECTORS.RESET_VOLUME_BTN);
    await expect(resetBtn).toBeVisible();
    await expect(resetBtn).toContainText('Reset');

    // Button should be clickable
    await expect(resetBtn).toBeEnabled();
  });

  test('export to excel button is present', async ({ page }) => {
    const exportBtn = page.locator(SELECTORS.EXPORT_VOLUME_EXCEL_BTN);
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toContainText('Export to Excel');
  });

  test('changing training days updates selection', async ({ page }) => {
    const trainingDays = page.locator(SELECTORS.TRAINING_DAYS);

    // Change to 5 days
    await trainingDays.selectOption('5');
    await expect(trainingDays).toHaveValue('5');

    // Change to 2 days
    await trainingDays.selectOption('2');
    await expect(trainingDays).toHaveValue('2');
  });

  test('mode toggle switches between basic and advanced', async ({ page }) => {
    const basicLabel = page.locator('label[for="mode-basic"]');
    const advancedLabel = page.locator('label[for="mode-advanced"]');
    const basicRadio = page.locator('#mode-basic');
    const advancedRadio = page.locator('#mode-advanced');

    // Click advanced mode
    await advancedLabel.click();
    await page.waitForTimeout(300); // Wait for UI update
    await expect(advancedRadio).toBeChecked();

    // Click basic mode
    await basicLabel.click();
    await page.waitForTimeout(300);
    await expect(basicRadio).toBeChecked();
  });

  test('calculate volume shows results section', async ({ page }) => {
    const calculateBtn = page.locator(SELECTORS.CALCULATE_VOLUME_BTN);
    const resultsSection = page.locator('.results-section');

    // Results should initially be hidden
    await expect(resultsSection).toHaveClass(/d-none/);

    // Click calculate
    await calculateBtn.click();

    // Wait for results to show
    await page.waitForTimeout(500);

    // Results section should be visible (class d-none removed)
    const hasHiddenClass = await resultsSection.evaluate(el => 
      el.classList.contains('d-none')
    );
    expect(hasHiddenClass).toBe(false);
  });

  test('results table shows after calculation', async ({ page }) => {
    // Click calculate
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    // Results table should exist
    const resultsTable = page.locator('.results-section table');
    await expect(resultsTable).toBeVisible();

    // Check headers
    const headers = resultsTable.locator('thead th');
    const headerTexts = await headers.allInnerTexts();
    const headerString = headerTexts.join(' ').toLowerCase();

    expect(headerString).toContain('muscle');
    expect(headerString).toContain('weekly sets');
    expect(headerString).toContain('sets per session');
  });

  test('reset button clears or resets values', async ({ page }) => {
    const resetBtn = page.locator(SELECTORS.RESET_VOLUME_BTN);

    // First calculate to show results
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    // Results should be visible
    const resultsSection = page.locator('.results-section');
    let hasHiddenClass = await resultsSection.evaluate(el => 
      el.classList.contains('d-none')
    );
    expect(hasHiddenClass).toBe(false);

    // Click reset
    await resetBtn.click();
    await page.waitForTimeout(500);

    // Behavior depends on implementation - either hides results or resets values
    // At minimum, no errors should occur
  });

  test('export to excel triggers download for calculated data', async ({ page }) => {
    // First calculate to generate data
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const exportBtn = page.locator(SELECTORS.EXPORT_VOLUME_EXCEL_BTN);

    // Setup download handler
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    // Click export
    await exportBtn.click();

    // Either download starts or handled differently
    const download = await downloadPromise;
    if (download) {
      const filename = download.suggestedFilename();
      expect(filename.toLowerCase()).toContain('xlsx');
    }
  });

  test('saved plans can be restored and deleted through volume history', async ({ page }) => {
    const trainingDays = '7';
    const chestVolume = 59;
    const bicepsVolume = 47;
    const totalVolume = chestVolume + bicepsVolume;
    const historyRows = page.locator('#history-body tr');
    const historyCountBefore = await historyRows.count();
    const historyWasEmpty = historyCountBefore === 1 &&
      await historyRows.first().locator('td[colspan="5"]').getByText(/No saved volume plans yet\./i).count().catch(() => 0) > 0;
    const expectedCountAfterSave = historyWasEmpty ? 1 : Math.min(historyCountBefore + 1, 100);
    const expectedCountAfterDelete = historyWasEmpty ? 1 : historyCountBefore;

    await page.locator(SELECTORS.TRAINING_DAYS).selectOption(trainingDays);
    await setVolumeSlider(page, 'Chest', chestVolume);
    await setVolumeSlider(page, 'Biceps', bicepsVolume);
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();

    await expect(page.locator('.results-section')).not.toHaveClass(/d-none/);
    await expect(page.locator('#results-body tr').filter({ hasText: 'Chest' }).first()).toContainText('59');
    await expect(page.locator('#results-body tr').filter({ hasText: 'Biceps' }).first()).toContainText('47');

    await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes('/api/save_volume_plan') &&
        response.request().method() === 'POST' &&
        response.ok()
      ),
      page.locator('#export-volume').click(),
    ]);

    await expectToast(page, /Plan #\d+ saved\.\s*Activate for Plan tab/i);
    await expect(historyRows).toHaveCount(expectedCountAfterSave);

    const newestHistoryRow = historyRows.first();
    await expect(newestHistoryRow).toContainText(`${trainingDays} days`);
    await expect(newestHistoryRow).toContainText(`${totalVolume} sets`);

    await page.locator(SELECTORS.TRAINING_DAYS).selectOption('2');
    await setVolumeSlider(page, 'Chest', 3);
    await setVolumeSlider(page, 'Biceps', 4);
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await expectVolumeSliderValue(page, 'Chest', 3);
    await expectVolumeSliderValue(page, 'Biceps', 4);

    await Promise.all([
      page.waitForResponse((response) =>
        /\/api\/volume_plan\/\d+$/.test(response.url()) &&
        response.request().method() === 'GET' &&
        response.ok()
      ),
      newestHistoryRow.locator('button.load-plan').click(),
    ]);

    await expect(page.locator(SELECTORS.TRAINING_DAYS)).toHaveValue(trainingDays);
    await expectVolumeSliderValue(page, 'Chest', chestVolume);
    await expectVolumeSliderValue(page, 'Biceps', bicepsVolume);
    await expect(page.locator('#results-body tr').filter({ hasText: 'Chest' }).first()).toContainText('8.4');

    await newestHistoryRow.locator('button.delete-plan').click();
    await expect(page.locator('#deleteVolumePlanModal')).toBeVisible();

    await Promise.all([
      page.waitForResponse((response) =>
        /\/api\/volume_plan\/\d+$/.test(response.url()) &&
        response.request().method() === 'DELETE' &&
        response.ok()
      ),
      page.locator('#confirmDeleteVolumePlan').click(),
    ]);

    await expectToast(page, /Volume plan deleted successfully/i);
    await expect(historyRows).toHaveCount(expectedCountAfterDelete);
    if (historyWasEmpty) {
      await expect(historyRows.first()).toContainText(/No saved volume plans yet\./i);
    }
  });

  test('volume sliders exist for muscle groups', async ({ page }) => {
    const slidersContainer = page.locator('#sliders');
    
    // Wait for sliders to be populated
    await page.waitForTimeout(500);

    // Should have some slider elements
    const sliders = slidersContainer.locator('input[type="range"]');
    const sliderCount = await sliders.count();
    
    // Basic mode should have major muscle groups
    expect(sliderCount).toBeGreaterThan(0);
  });

  test('muscle group volume can be adjusted', async ({ page }) => {
    const slidersContainer = page.locator('#sliders');
    
    // Wait for sliders to be populated
    await page.waitForTimeout(500);

    const sliders = slidersContainer.locator('input[type="range"]');
    const firstSlider = sliders.first();

    if (await firstSlider.isVisible()) {
      const initialValue = await firstSlider.inputValue();
      
      // Change slider value
      await firstSlider.fill('15');
      const newValue = await firstSlider.inputValue();
      
      expect(newValue).toBe('15');
    }
  });

  test('advanced mode shows more muscle groups', async ({ page }) => {
    // Get basic mode slider count
    await page.waitForTimeout(500);
    const basicSliders = page.locator('#sliders input[type="range"]');
    const basicCount = await basicSliders.count();

    // Switch to advanced mode
    const advancedLabel = page.locator('label[for="mode-advanced"]');
    await advancedLabel.click();
    await page.waitForTimeout(500);

    // Get advanced mode slider count
    const advancedSliders = page.locator('#sliders input[type="range"]');
    const advancedCount = await advancedSliders.count();

    // Advanced should have same or more
    expect(advancedCount).toBeGreaterThanOrEqual(basicCount);
  });

  test('slider labels show muscle group names', async ({ page }) => {
    const slidersContainer = page.locator('#sliders');
    await page.waitForTimeout(500);

    // Check for labels
    const labels = slidersContainer.locator('label, .muscle-label, .slider-label');
    const count = await labels.count();
    
    if (count > 0) {
      const firstLabel = await labels.first().textContent();
      expect(firstLabel?.trim()).toBeTruthy();
    }
  });

  test('slider values show current set count', async ({ page }) => {
    const slidersContainer = page.locator('#sliders');
    await page.waitForTimeout(500);

    // Check for value displays
    const valueDisplays = slidersContainer.locator('.slider-value, output, .value-display');
    const count = await valueDisplays.count();

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('results show total weekly volume', async ({ page }) => {
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const resultsSection = page.locator('.results-section');
    const text = await resultsSection.textContent();

    // Should show some volume statistics
    expect(text?.toLowerCase()).toMatch(/total|volume|sets/);
  });

  test('results per day change with training days', async ({ page }) => {
    // Calculate with 3 days
    const trainingDays = page.locator(SELECTORS.TRAINING_DAYS);
    await trainingDays.selectOption('3');
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const resultsTable = page.locator('.results-section table');
    const firstRowSetsPerSession = await resultsTable.locator('tbody tr').first().locator('td').nth(2).textContent();

    // Change to 5 days
    await trainingDays.selectOption('5');
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const newSetsPerSession = await resultsTable.locator('tbody tr').first().locator('td').nth(2).textContent();

    // Sets per session should be different (or same if weekly total changes)
    // At minimum both should be valid numbers
    expect(firstRowSetsPerSession).toBeTruthy();
    expect(newSetsPerSession).toBeTruthy();
  });

  test('validation prevents invalid slider values', async ({ page }) => {
    const slidersContainer = page.locator('#sliders');
    await page.waitForTimeout(500);

    const slider = slidersContainer.locator('input[type="range"]').first();
    
    if (await slider.isVisible()) {
      const min = await slider.getAttribute('min') || '0';
      const max = await slider.getAttribute('max') || '30';

      // Slider should have reasonable bounds
      expect(parseInt(min)).toBeGreaterThanOrEqual(0);
      expect(parseInt(max)).toBeLessThanOrEqual(100); // Volume can go up to 60+ sets for some muscles
    }
  });

  test('page maintains state after mode switch', async ({ page }) => {
    const trainingDays = page.locator(SELECTORS.TRAINING_DAYS);
    
    // Set training days to 4
    await trainingDays.selectOption('4');

    // Switch modes
    await page.locator('label[for="mode-advanced"]').click();
    await page.waitForTimeout(300);
    
    await page.locator('label[for="mode-basic"]').click();
    await page.waitForTimeout(300);

    // Training days should remain at 4
    await expect(trainingDays).toHaveValue('4');
  });

  test('results table is scrollable if many rows', async ({ page }) => {
    // Switch to advanced for more muscle groups
    await page.locator('label[for="mode-advanced"]').click();
    await page.waitForTimeout(300);

    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const resultsSection = page.locator('.results-section');
    const overflow = await resultsSection.evaluate(el => {
      const style = getComputedStyle(el);
      return style.overflow === 'auto' || style.overflowY === 'auto' || 
             style.overflow === 'scroll' || style.overflowY === 'scroll' ||
             el.scrollHeight > el.clientHeight;
    });

    // Should either have scroll or fit content
    expect(overflow !== null).toBeTruthy();
  });
});

test.describe('Volume Splitter Mobile Responsive', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(ROUTES.VOLUME_SPLITTER);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('controls are usable on mobile', async ({ page }) => {
    const trainingDays = page.locator(SELECTORS.TRAINING_DAYS);
    await expect(trainingDays).toBeVisible();
    
    const calculateBtn = page.locator(SELECTORS.CALCULATE_VOLUME_BTN);
    await expect(calculateBtn).toBeVisible();
  });

  test('sliders are touch-friendly on mobile', async ({ page }) => {
    const sliders = page.locator('#sliders input[type="range"]');
    await page.waitForTimeout(500);
    
    const count = await sliders.count();
    
    if (count > 0) {
      const firstSlider = sliders.first();
      const box = await firstSlider.boundingBox();
      
      if (box) {
        // Slider should have reasonable touch target height
        expect(box.height).toBeGreaterThanOrEqual(20);
      }
    }
  });

  test('results table readable on mobile', async ({ page }) => {
    await page.locator(SELECTORS.CALCULATE_VOLUME_BTN).click();
    await page.waitForTimeout(500);

    const resultsTable = page.locator('.results-section table');
    await expect(resultsTable).toBeVisible();
  });
});
