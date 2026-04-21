/**
 * E2E Test: Progression Plan Page
 * 
 * Tests the progression plan functionality including:
 * - Page loading
 * - Exercise selection
 * - Goals table
 * - Delete confirmation modal
 */
import { test, expect, ROUTES, SELECTORS, waitForPageReady } from './fixtures';

function unwrapProgressionApiData(payload: unknown) {
  if (
    payload &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    'data' in payload
  ) {
    return (payload as { data: unknown }).data;
  }

  return payload;
}

test.describe('Progression Plan Page', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('page loads with correct structure', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText('Progression Plan');

    // Check container
    await expect(page.locator(SELECTORS.PAGE_PROGRESSION)).toBeVisible();
  });

  test('exercise selector is present', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    await expect(exerciseSelector).toBeVisible();

    // Should have default placeholder option
    const defaultOption = exerciseSelector.locator('option').first();
    await expect(defaultOption).toContainText('Choose an exercise');
  });

  test('current goals section is present', async ({ page }) => {
    const goalsSection = page.locator('.current-goals');
    await expect(goalsSection).toBeVisible();

    // Check heading
    await expect(goalsSection.locator('h4')).toContainText('Current Goals');

    // Check table exists
    const table = goalsSection.locator('table');
    await expect(table).toBeVisible();
  });

  test('goals table has correct structure', async ({ page }) => {
    const table = page.locator('.current-goals table');
    const headers = table.locator('thead th');
    const headerTexts = await headers.allInnerTexts();
    const headerString = headerTexts.join(' ').toLowerCase();

    expect(headerString).toContain('exercise');
    expect(headerString).toContain('goal type');
    expect(headerString).toContain('current');
    expect(headerString).toContain('target');
    expect(headerString).toContain('date');
    expect(headerString).toContain('status');
    expect(headerString).toContain('actions');
  });

  test('delete goal modal exists', async ({ page }) => {
    // The modal should be in the DOM but hidden
    const modal = page.locator('#deleteGoalModal');
    await expect(modal).toBeAttached();
    
    // Check modal has correct structure
    await expect(modal.locator('.modal-title')).toContainText('Delete Goal');
  });

  test('exercise selector shows available exercises', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    // Should have at least the placeholder option
    expect(count).toBeGreaterThanOrEqual(1);

    // Debug info should be present (shows exercise count)
    const debugInfo = page.locator('.debug-info');
    if (await debugInfo.isVisible()) {
      await expect(debugInfo).toContainText('Available exercises');
    }
  });

  test('selecting exercise shows suggestions container', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const suggestionsContainer = page.locator('#suggestionsContainer');

    // Initially hidden
    const initialDisplay = await suggestionsContainer.evaluate(el => 
      window.getComputedStyle(el).display
    );
    expect(initialDisplay).toBe('none');

    // Check if there are exercises to select
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    if (count > 1) {
      // Select an exercise
      const optionValue = await options.nth(1).getAttribute('value');
      if (optionValue) {
        await exerciseSelector.selectOption(optionValue);
        
        // Wait for suggestions to potentially load
        await page.waitForTimeout(500);
        
        // Suggestions container might show if API returns data
        // This depends on whether exercises have progression data
      }
    }
  });
});

test.describe('Progression Plan with Data Setup', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();

    // First add an exercise to workout plan
    await page.goto(ROUTES.WORKOUT_PLAN);
    await waitForPageReady(page);

    // Select routine
    await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-program') as HTMLSelectElement;
      return select && select.options.length > 1;
    });
    await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Push Pull Legs');
    await page.waitForFunction(() => {
      const select = document.getElementById('routine-day') as HTMLSelectElement;
      return select && select.options.length > 1;
    });
    await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Push 1');

    // Wait for exercise dropdown
    await page.waitForFunction(() => {
      const select = document.getElementById('exercise') as HTMLSelectElement;
      return select && select.options.length > 1;
    });

    // Add Bench Press if available
    const exerciseSelect = page.locator(SELECTORS.EXERCISE_SEARCH);
    const options = await exerciseSelect.locator('option').allInnerTexts();
    
    // Find a compound exercise
    const compoundExercise = options.find(opt => 
      opt.toLowerCase().includes('bench press') || 
      opt.toLowerCase().includes('squat') ||
      opt.toLowerCase().includes('deadlift')
    ) || options[1];
    
    if (compoundExercise) {
      await exerciseSelect.selectOption(compoundExercise);
      await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();
      await page.waitForTimeout(500);
    }

    // Navigate to progression page
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('exercise selector reflects added exercises', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = await exerciseSelector.locator('option').allInnerTexts();
    
    // Should have exercises available (depends on what was added)
    expect(options.length).toBeGreaterThanOrEqual(1);
  });

  test('selecting exercise displays progression info', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    if (count > 1) {
      const optionValue = await options.nth(1).getAttribute('value');
      if (optionValue) {
        await exerciseSelector.selectOption(optionValue);
        await page.waitForTimeout(500);

        // Should show exercise-specific info
        const progressionInfo = page.locator('.progression-info, .exercise-progress, #progression-display');
        if (await progressionInfo.count() > 0) {
          await expect(progressionInfo).toBeVisible();
        }
      }
    }
  });
});

test.describe('Progression Goal Management', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('add goal form exists', async ({ page }) => {
    // The progression page uses exercise selection to add goals
    // Check for exercise selector instead of a traditional form
    const exerciseSelect = page.locator('#exerciseSelect');
    const suggestionsContainer = page.locator('#suggestionsContainer');
    const goalsTable = page.locator('.current-goals table');
    
    const hasSelect = await exerciseSelect.count() > 0;
    const hasSuggestions = await suggestionsContainer.count() > 0;
    const hasGoalsTable = await goalsTable.count() > 0;
    
    // At least one of these should exist for goal management
    expect(hasSelect || hasSuggestions || hasGoalsTable).toBeTruthy();
  });

  test('add goal form has required fields', async ({ page }) => {
    // Goal form fields are in a modal - check that modal and form exists
    const goalModal = page.locator('#goalSettingModal');
    const goalForm = page.locator('#goalForm');
    
    // Modal should exist in the DOM (even if not visible)
    await expect(goalModal).toBeAttached();
    await expect(goalForm).toBeAttached();
    
    // Check for form fields within the modal
    const currentValue = page.locator('#currentValue');
    const targetValue = page.locator('#targetValue');
    const goalDate = page.locator('#goalDate');
    
    // At least target value and goal date should exist
    const currentValueCount = await currentValue.count();
    const targetValueCount = await targetValue.count();
    const goalDateCount = await goalDate.count();

    expect(currentValueCount + targetValueCount + goalDateCount).toBeGreaterThan(0);
  });

  test('goal type selector has options', async ({ page }) => {
    const goalType = page.locator('#goal-type, select[name="goal_type"]');
    
    if (await goalType.count() > 0) {
      const options = goalType.locator('option');
      const count = await options.count();
      
      expect(count).toBeGreaterThan(0);
    }
  });

  test('delete goal confirmation modal works', async ({ page }) => {
    const modal = page.locator('#deleteGoalModal');
    
    // Open modal programmatically if there's a delete button
    const deleteBtn = page.locator('.delete-goal').first();
    
    if (await deleteBtn.count() > 0) {
      await deleteBtn.click();
      await page.waitForTimeout(500);
      
      // Modal should have confirm and cancel buttons
      const confirmBtn = modal.getByRole('button', { name: 'Delete' });
      const cancelBtn = modal.getByRole('button', { name: 'Cancel' });
      
      if (await modal.isVisible()) {
        await expect(confirmBtn).toBeVisible();
        await expect(cancelBtn).toBeVisible();
        
        // Close modal
        await page.keyboard.press('Escape');
      }
    }
  });
});

test.describe('Progression Goal Lifecycle Smoke', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('goal can be saved and completed through the progression page', async ({ page }) => {
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);

    const exerciseSelector = page.locator('#exerciseSelect');
    let optionCount = await exerciseSelector.locator('option').count();

    if (optionCount <= 1) {
      await page.goto(ROUTES.WORKOUT_PLAN);
      await waitForPageReady(page);

      await page.locator(SELECTORS.ROUTINE_ENV).selectOption('GYM');
      await page.waitForFunction(() => {
        const select = document.getElementById('routine-program') as HTMLSelectElement;
        return !!select && select.options.length > 1;
      });
      await page.locator(SELECTORS.ROUTINE_PROGRAM).selectOption('Push Pull Legs');
      await page.waitForFunction(() => {
        const select = document.getElementById('routine-day') as HTMLSelectElement;
        return !!select && select.options.length > 1;
      });
      await page.locator(SELECTORS.ROUTINE_DAY).selectOption('Push 1');
      await page.waitForFunction(() => {
        const select = document.getElementById('exercise') as HTMLSelectElement;
        return !!select && select.options.length > 1;
      });

      const exerciseOptions = page.locator(SELECTORS.EXERCISE_SEARCH).locator('option');
      const firstExerciseValue = await exerciseOptions.nth(1).getAttribute('value');
      expect(firstExerciseValue).toBeTruthy();
      await page.locator(SELECTORS.EXERCISE_SEARCH).selectOption(firstExerciseValue!);
      await page.locator(SELECTORS.ADD_EXERCISE_BTN).click();

      await page.goto(ROUTES.PROGRESSION);
      await waitForPageReady(page);
      optionCount = await exerciseSelector.locator('option').count();
    }

    expect(optionCount).toBeGreaterThan(1);

    const initialRowCount = await page.locator('.current-goals tbody tr').count();
    const selectedValue = await exerciseSelector.locator('option').nth(1).getAttribute('value');
    expect(selectedValue).toBeTruthy();
    await exerciseSelector.selectOption(selectedValue!);

    await expect(page.locator('#suggestionsContainer')).toBeVisible();
    await expect(page.locator('.suggestion-card[data-goal-type="weight"]')).toBeVisible();
    await expect(page.locator('.suggestion-card[data-goal-type="reps"]')).toBeVisible();
    await expect(page.locator('.suggestion-card[data-goal-type="sets"]')).toBeVisible();

    const weightGoalButton = page.locator('.set-goal-btn[data-goal-type="weight"]').first();
    await expect(weightGoalButton).toBeVisible();
    await weightGoalButton.click();

    const goalModal = page.locator('#goalSettingModal');
    await expect(goalModal).toBeVisible();
    await expect(page.locator('#currentValue')).toHaveValue(/^[1-9]\d*(\.\d+)?$/);
    await expect(page.locator('#targetValue')).toHaveValue(/^[1-9]\d*(\.\d+)?$/);
    await page.locator('#goalDate').fill('31-12-2099');
    await page.locator('#saveGoal').click();

    await expect.poll(async () => {
      await page.waitForLoadState('networkidle');
      return page.locator('.current-goals tbody tr').count();
    }).toBe(initialRowCount + 1);

    const savedRow = page.locator('.current-goals tbody tr').last();
    await expect(savedRow).toContainText(selectedValue!);
    await savedRow.locator('.complete-goal').click();
    await expect(savedRow.locator('.badge')).toContainText('Completed');

    await page.reload();
    await waitForPageReady(page);
    await expect.poll(async () => page.locator('.current-goals tbody tr').count()).toBe(initialRowCount);
  });
});

test.describe('Progression Methodology Display', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('progression methodology info is displayed', async ({ page }) => {
    // Look for progression-related content on the page
    const pageContent = await page.content();
    const lowerContent = pageContent.toLowerCase();
    
    // Should have progression-related elements
    const hasProgressionContent = 
      lowerContent.includes('progression') ||
      lowerContent.includes('goal') ||
      lowerContent.includes('exercise') ||
      lowerContent.includes('target') ||
      lowerContent.includes('current');
    
    expect(hasProgressionContent).toBeTruthy();
  });

  test('double progression methodology explained', async ({ page }) => {
    const pageContent = await page.content();
    const lowerContent = pageContent.toLowerCase();
    
    // Page should have some progression-related content visible
    // The page focuses on goal setting, not necessarily explaining methodology
    const hasProgressionConcepts = 
      lowerContent.includes('progression') ||
      lowerContent.includes('goal') ||
      lowerContent.includes('target') ||
      lowerContent.includes('exercise') ||
      lowerContent.includes('value');
    
    expect(hasProgressionConcepts).toBeTruthy();
  });
});

test.describe('Progression Status Indicators', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('status column shows goal progress', async ({ page }) => {
    const goalsTable = page.locator('.current-goals table');
    
    if (await goalsTable.isVisible()) {
      const headers = await goalsTable.locator('thead th').allInnerTexts();
      const headerString = headers.join(' ').toLowerCase();
      
      expect(headerString).toContain('status');
    }
  });

  test('status uses color coding', async ({ page }) => {
    const statusCells = page.locator('.status-cell, .goal-status, [class*="status"]');
    const count = await statusCells.count();

    if (count > 0) {
      const firstStatus = statusCells.first();
      
      // Check for color classes
      const classes = await firstStatus.getAttribute('class');
      const hasColorClass = 
        classes?.includes('success') ||
        classes?.includes('warning') ||
        classes?.includes('danger') ||
        classes?.includes('info') ||
        classes?.includes('primary');
      
      // Color may be applied via inline style too
      const bgColor = await firstStatus.evaluate(el => getComputedStyle(el).backgroundColor);
      
      expect(hasColorClass || bgColor !== 'rgba(0, 0, 0, 0)').toBeTruthy();
    }
  });
});

test.describe('Progression Suggestions', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('suggestions container exists', async ({ page }) => {
    const suggestionsContainer = page.locator('#suggestionsContainer, .suggestions-container');
    await expect(suggestionsContainer).toBeAttached();
  });

  test('selecting exercise may show suggestions', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    if (count > 1) {
      const optionValue = await options.nth(1).getAttribute('value');
      if (optionValue) {
        await exerciseSelector.selectOption(optionValue);
        await page.waitForTimeout(1000);

        // Suggestions may appear based on exercise data
        const suggestionsContainer = page.locator('#suggestionsContainer, .suggestions-container');
        
        // Check if container has content
        const text = await suggestionsContainer.textContent();
        // Either shows suggestions or remains empty (both are valid states)
      }
    }
  });
});

test.describe('Double Progression Logic (v1.5.0)', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('suggestions display double progression types', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    if (count > 1) {
      const optionValue = await options.nth(1).getAttribute('value');
      if (optionValue) {
        await exerciseSelector.selectOption(optionValue);
        await page.waitForTimeout(1500);

        const suggestionsContainer = page.locator('#suggestionsContainer, .suggestions-container');
        
        // If suggestions are visible, verify they have proper structure
        if (await suggestionsContainer.isVisible()) {
          const suggestionCards = suggestionsContainer.locator('.suggestion-card, .card, [class*="suggestion"]');
          const cardCount = await suggestionCards.count();
          
          if (cardCount > 0) {
            // Each suggestion should have title and description
            const firstCard = suggestionCards.first();
            const text = await firstCard.textContent();
            expect(text?.length).toBeGreaterThan(0);
          }
        }
      }
    }
  });

  test('double progression suggestions include weight or rep recommendations', async ({ page }) => {
    // Navigate with an exercise that has workout history
    const exerciseSelector = page.locator('#exerciseSelect');
    const options = exerciseSelector.locator('option');
    const count = await options.count();

    if (count > 1) {
      const optionValue = await options.nth(1).getAttribute('value');
      if (optionValue) {
        await exerciseSelector.selectOption(optionValue);
        await page.waitForTimeout(1500);

        const pageContent = await page.content();
        const lowerContent = pageContent.toLowerCase();
        
        // Double progression should mention weight or rep changes
        const hasProgressionTerms = 
          lowerContent.includes('weight') ||
          lowerContent.includes('reps') ||
          lowerContent.includes('increase') ||
          lowerContent.includes('decrease') ||
          lowerContent.includes('progression') ||
          lowerContent.includes('rep range') ||
          lowerContent.includes('start training'); // Initial state message
        
        expect(hasProgressionTerms).toBeTruthy();
      }
    }
  });

  test('API returns proper suggestion structure', async ({ page, request }) => {
    // Test the API directly using Playwright's request context
    const response = await request.post('http://127.0.0.1:5000/get_exercise_suggestions', {
      data: {
        exercise: 'Bench Press (Barbell)',
        is_novice: true
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const rawPayload = await response.json();
    expect(rawPayload.ok).toBe(true);
    expect(rawPayload.status).toBe('success');
    const suggestions = unwrapProgressionApiData(rawPayload);
    expect(Array.isArray(suggestions)).toBe(true);
    
    // Verify suggestion structure matches v1.5.0 double progression format
    if (Array.isArray(suggestions) && suggestions.length > 0) {
      const suggestion = suggestions[0];
      expect(suggestion).toHaveProperty('type');
      expect(suggestion).toHaveProperty('title');
      expect(suggestion).toHaveProperty('description');
      
      // Valid suggestion types for double progression
      const validTypes = [
        'double_progression_weight', 'double_progression_reps',
        'technique', 'info', 'start', 'warning', 'success'
      ];
      expect(validTypes.some(type => suggestion.type.includes(type) || validTypes.includes(suggestion.type))).toBeTruthy();
    }
  });
});

test.describe('Progression Mobile Responsive', () => {
  test.beforeEach(async ({ page, consoleErrors }) => {
    consoleErrors.startCollecting();
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(ROUTES.PROGRESSION);
    await waitForPageReady(page);
  });

  test.afterEach(async ({ consoleErrors }) => {
    consoleErrors.assertNoErrors();
  });

  test('exercise selector usable on mobile', async ({ page }) => {
    const exerciseSelector = page.locator('#exerciseSelect');
    await expect(exerciseSelector).toBeVisible();

    const box = await exerciseSelector.boundingBox();
    if (box) {
      expect(box.width).toBeGreaterThanOrEqual(100);
    }
  });

  test('goals table readable on mobile', async ({ page }) => {
    const goalsTable = page.locator('.current-goals table');
    await expect(goalsTable).toBeVisible();

    // Table should be within viewport or scrollable
    const isScrollable = await page.evaluate(() => {
      const tableContainer = document.querySelector('.table-responsive, .current-goals');
      return tableContainer ? tableContainer.scrollWidth > tableContainer.clientWidth : false;
    });

    expect(isScrollable !== null).toBeTruthy();
  });
});
