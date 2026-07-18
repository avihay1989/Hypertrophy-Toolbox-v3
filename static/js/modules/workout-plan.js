import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { workoutPlanState } from './workout-plan-state.js';
import {
    configureWorkoutPlanTable,
    handleViewModeChange,
    initializeRoutineTabs,
    transformMuscleDisplay,
    updateRoutineTabs,
    updateWorkoutPlanTable,
} from './workout-plan-table.js';
import { applyRoutineTabFilter } from './workout-plan-helpers.js';
import {
    applyUserProfileEstimateForSelectedExercise,
    bindEstimateTraceToggle,
    initializeWeightDirtyTracking,
    neutralizeEstimateState,
    resetWeightUserDirty,
} from './workout-plan-estimates.js';
import {
    configureExecutionStyle,
    showExecutionStylePicker,
} from './workout-plan-execution-style.js';
import { handleSwapExercise } from './workout-plan-replacement.js';
import {
    configureAddExercise,
    handleAddExercise,
    initializeDefaultValues,
    setFieldValidationState,
} from './workout-plan-add-exercise.js';
import {
    configureSupersets,
    handleSupersetCheckboxChange,
    initializeSupersetActions,
    updateSupersetActionButtons,
} from './workout-plan-supersets.js';
import { initializeWorkoutPlanMedia } from './workout-plan-media.js';
import {
    applyWorkoutControlDefaults,
    beginHydration,
    clearWorkoutControls,
    endHydration,
    restoreWorkoutControls,
    saveWorkoutControls,
    withHydrationSuppressed,
    WORKOUT_CONTROL_DEFAULTS,
    WORKOUT_CONTROL_IDS,
} from './workout-controls-persistence.js';

initializeWorkoutPlanMedia();

// Re-export the table renderer so existing importers (and the workout-plan E2E
// harness that imports this module directly) keep resolving it from here.
export { updateWorkoutPlanTable };

// Re-export the profile-estimate entry point so existing importers keep
// resolving it from this module after the WP3.4c estimates split.
export { applyUserProfileEstimateForSelectedExercise };

// Re-export the Add Exercise handler so app.js and the existing window bridge
// keep resolving it from this module after the WP3.4f split.
export { handleAddExercise };

// Wire the table module's injected feature callbacks — swap, superset toggle,
// superset action init, execution-style click, and plan refresh — at load, so a
// bare updateWorkoutPlanTable() (e.g. the E2E media harness) renders identically.
configureWorkoutPlanTable({
    onSwap: handleSwapExercise,
    onSupersetToggle: handleSupersetCheckboxChange,
    onExecutionStyleClick: showExecutionStylePicker,
    updateSupersetActionButtons,
    initializeSupersetActions,
    refreshPlan: fetchWorkoutPlan,
});

// Wire the execution-style picker's plan-refresh callback (orchestration that
// stays here) so it never imports back into this monolith.
configureExecutionStyle({ refreshPlan: fetchWorkoutPlan });

// Wire the Add Exercise submission refresh without importing this entry module
// back into the feature module.
configureAddExercise({ refreshPlan: fetchWorkoutPlan });

// Wire the superset link/unlink refresh without importing this entry module
// back into the feature module.
configureSupersets({ refreshPlan: fetchWorkoutPlan });

/**
 * Helper function to handle standardized API responses
 * @param {Response} response - Fetch response object
 * @returns {Promise<Object>} Extracted data or throws error
 * @deprecated Use api wrapper from fetch-wrapper.js instead
 */
async function handleApiResponse(response) {
    const data = await response.json();
    
    // Check if response is in standardized format
    if (data.ok === false) {
        const errorMsg = data.error?.message || data.error || 'An error occurred';
        throw new Error(errorMsg);
    }
    
    // If response.ok is true, return the data property, otherwise return the entire object (backward compatibility)
    return data.ok === true ? (data.data !== undefined ? data.data : data) : data;
}

// Workout plan functionality
export async function fetchWorkoutPlan() {
    try {
        const data = await api.get('/get_workout_plan');
        
        // api wrapper returns the response data directly (from data.data if standardized)
        const exercises = data.data !== undefined ? data.data : data;
        
        // Cache all exercises for tab filtering
        workoutPlanState.allExercisesCache = exercises;
        
        // Update routine tabs based on available routines
        updateRoutineTabs(exercises);
        
        // Apply current tab filter and render
        const filteredExercises = applyRoutineTabFilter(exercises, workoutPlanState.currentRoutineTabFilter);
        updateWorkoutPlanTable(filteredExercises);
        updateWorkoutPlanUI(exercises); // Always show totals for all exercises
        
        // Table responsiveness is already initialized by table-responsiveness.js autoInit
        // No need to reinitialize here
    } catch (error) {
        console.error('Error loading workout plan:', error);
        // api wrapper already shows error toast, but we can show a fallback
        if (!error.code) {
            showToast(error.message || 'Failed to load workout plan', true);
        }
    }
}

    const WORKOUT_PLAN_DEBUG = false;
    const workoutPlanDebugLog = (...args) => {
        if (WORKOUT_PLAN_DEBUG) {
            console.log(...args);
        }
    };

export async function updateExerciseDetails(exercise) {
    if (!exercise) return;

    const detailsContainer = document.getElementById('exercise-details');
    if (!detailsContainer) return;

    try {
        const data = await api.get(`/get_exercise_info/${exercise}`, { showLoading: false, showErrorToast: false });
        const info = data.data || data;
        
        detailsContainer.innerHTML = `
            <div class="exercise-info">
                <h5>Exercise Details</h5>
                <div class="detail-row">
                    <span class="detail-label">Primary Muscle:</span>
                    <span class="detail-value">${transformMuscleDisplay(info.primary_muscle_group, 'primary', info.advanced_isolated_muscles)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Secondary Muscle:</span>
                    <span class="detail-value">${transformMuscleDisplay(info.secondary_muscle_group, 'primary', info.advanced_isolated_muscles)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Equipment:</span>
                    <span class="detail-value">${info.equipment || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Force Type:</span>
                    <span class="detail-value">${info.force || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Level:</span>
                    <span class="detail-value">${info.level || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Mechanic:</span>
                    <span class="detail-value">${info.mechanic || 'N/A'}</span>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error fetching exercise details:', error);
        showToast(error.message || 'Failed to load exercise details', true);
    }
}

export async function updateExerciseForm(exercise) {
    if (!exercise) return;

    // Preserve the currently selected routine
    const selectedRoutine = document.getElementById('routine').value;

    // KI-005 cleanup: source the fallback defaults from the single pinned set in
    // the persistence module (its keys are exactly the six control ids) instead
    // of a third hardcoded copy, so the "single source of defaults" claim holds.
    const defaultValues = WORKOUT_CONTROL_DEFAULTS;

    try {
        const data = await api.get(`/get_exercise_info/${exercise}`, { showLoading: false, showErrorToast: false });
        const info = data.data || data;
        
        // Set values with fallback to defaults
        document.getElementById('sets').value = info.recommended_sets || defaultValues.sets;
        document.getElementById('min_rep').value = info.min_reps || defaultValues.min_rep;
        document.getElementById('max_rep_range').value = info.max_reps || defaultValues.max_rep_range;
        document.getElementById('rir').value = info.recommended_rir || defaultValues.rir;
        document.getElementById('weight').value = info.recommended_weight || defaultValues.weight;
        document.getElementById('rpe').value = info.rpe_based ? (info.recommended_rpe || defaultValues.rpe) : defaultValues.rpe;

        // Restore the selected routine
        if (selectedRoutine) {
            document.getElementById('routine').value = selectedRoutine;
        }
    } catch (error) {
        console.error('Error updating exercise form:', error);
        showToast(error.message || 'Failed to load exercise recommendations', true);

        // On error, set default values
        document.getElementById('sets').value = defaultValues.sets;
        document.getElementById('min_rep').value = defaultValues.min_rep;
        document.getElementById('max_rep_range').value = defaultValues.max_rep_range;
        document.getElementById('rir').value = defaultValues.rir;
        document.getElementById('weight').value = defaultValues.weight;
        document.getElementById('rpe').value = defaultValues.rpe;
    }

    // KI-005 cleanup: no persistence hook here. `updateExerciseForm()` has no
    // in-app caller — it is reached only through the legacy `window.updateExerciseForm`
    // global (static/js/app.js) — so the deliberate-selection save lives on the
    // exercise `change` handler (handleExerciseSelection), which is the real path.
}

function handleExerciseSelection() {
    const exerciseSelect = document.getElementById('exercise');
    if (!exerciseSelect) return;

    exerciseSelect.addEventListener('change', (e) => {
        const selectedExercise = e.target.value;

        // KI-005 criterion 5 (OWNER-4 ruling): an EMPTY selection must not touch
        // the six Workout Controls AT ALL. Clearing the dropdown is not a
        // deliberate exercise choice — it happens on Clear Filters
        // (filters.js clearFilters()) and whenever a filter/routine rebuild
        // drops the current selection (updateExerciseDropdown() below). The
        // estimate path writes the generic default estimate into all six
        // controls but skips the save, which desynced the DOM from
        // sessionStorage and resurrected the cleared values on the next reload.
        // Writing-and-saving the defaults instead is explicitly rejected: that
        // would CLEAR the controls, contradicting criterion 5's "retain".
        //
        // KI-005 / OWNER-10: the six controls stay put, but the estimate-ONLY UI
        // from the previously selected exercise must not keep claiming (or acting
        // on) an exercise that is no longer selected. Neutralize it — display/state
        // cleanup only, no control-value write, no estimate request.
        if (!selectedExercise) {
            neutralizeEstimateState();
            return;
        }

        // Clear validation error when user selects a valid value
        setFieldValidationState('exercise', false);
        updateExerciseDetails(selectedExercise);

        // A deliberate exercise selection is the one-shot trigger that
        // re-applies the profile estimate (Issue #5). Reset the dirty flag so
        // the new estimate overwrites whatever the user typed for the previous
        // exercise.
        resetWeightUserDirty();
        void applyUserProfileEstimateForSelectedExercise().then(() => {
            // KI-005 (AR-1 × OWNER-1.3): a DELIBERATE selection's recommendation
            // IS the intended displayed state, so persist it.
            saveWorkoutControls();
        });
    });
}

export function handleRoutineSelection() {
    const routineSelect = document.getElementById('routine');
    const exerciseSelect = document.getElementById('exercise');
    if (!routineSelect || !exerciseSelect) return;

    routineSelect.addEventListener('change', async (e) => {
        try {
            const selectedRoutine = e.target.value;
            
            // Clear validation error when user selects a valid routine
            if (selectedRoutine) {
                setFieldValidationState('routine', false);
            }
            
            if (!selectedRoutine) {
                // If routine is cleared, reapply filters (if any) or show all exercises
                const { filterExercises } = await import('./filters.js');
                await filterExercises(true); // Preserve selection when clearing routine
                return;
            }

            // Store the selected routine
            routineSelect.dataset.selectedRoutine = selectedRoutine;

            // Check if there are active filters
            const filters = {};
            const filterElements = document.querySelectorAll('#filters-form select.filter-dropdown');
            filterElements.forEach(select => {
                if (select.value && select.id !== 'exercise' && select.id !== 'routine') {
                    const filterKey = select.dataset.filterKey || select.id;
                    filters[filterKey] = select.value;
                }
            });

            // If there are active filters, apply them to get filtered exercises
            if (Object.keys(filters).length > 0) {
                    workoutPlanDebugLog('DEBUG: Applying filters after routine selection:', filters);
                const { filterExercises } = await import('./filters.js');
                // Preserve the currently selected exercise when reapplying filters
                await filterExercises(true);
            } else {
                // No active filters, fetch exercises for the selected routine
                const data = await api.get(`/get_routine_exercises/${encodeURIComponent(selectedRoutine)}`, { showLoading: false, showErrorToast: false });
                const exercises = data.data || data;
                
                // Update exercise dropdown and maintain selection if possible
                const currentExercise = exerciseSelect.value;
                updateExerciseDropdown(exercises, currentExercise);
            }

        } catch (error) {
            console.error('Error fetching routine exercises:', error);
            showToast('Failed to load exercises for routine', true);
        }
    });
}

function updateExerciseDropdown(exercises, currentExercise = '') {
    const exerciseDropdown = document.getElementById('exercise');
    if (!exerciseDropdown) return;

    // Store current selection
    const previousValue = currentExercise || exerciseDropdown.value;

    // Clear and rebuild dropdown
    exerciseDropdown.innerHTML = '<option value="">Select Exercise</option>';
    
    if (Array.isArray(exercises)) {
        exercises.forEach(exercise => {
            const option = document.createElement('option');
            option.value = exercise;
            option.textContent = exercise;
            // Restore previous selection if it exists in new options
            if (exercise === previousValue) {
                option.selected = true;
            }
            exerciseDropdown.appendChild(option);
        });
    }

    // Trigger change event if the value changed
    if (exerciseDropdown.value !== previousValue) {
        exerciseDropdown.dispatchEvent(new Event('change'));
    }

    // Add visual feedback
    exerciseDropdown.classList.add('filter-applied');
    setTimeout(() => {
        exerciseDropdown.classList.remove('filter-applied');
    }, 2000);
}

export function updateWorkoutPlanUI(data) {
    // Update summary statistics
    const totalSets = data.reduce((sum, item) => sum + (parseInt(item.sets) || 0), 0);
    const totalExercises = data.length;
    
    const statsContainer = document.getElementById('workout-stats');
    if (statsContainer) {
        statsContainer.innerHTML = `
            <div class="stat-item">
                <h6>Total Exercises</h6>
                <span>${totalExercises}</span>
            </div>
            <div class="stat-item">
                <h6>Total Sets</h6>
                <span>${totalSets}</span>
            </div>
        `;
    }
}

/**
 * KI-005 — attach the Workout Controls capture listeners. Called only after
 * hydration has restored the stored record (OWNER-1.2).
 *
 * `input` (AR-4 ruling) is the capture trigger: synchronous, no debounce, and
 * purely a read — it never clamps, parses back into, or otherwise mutates the
 * field, so a mid-entry value survives a reload without the user ever blurring.
 * The pre-existing `change` handler (registered above, so it runs first) still
 * owns commit-time clamping; the listener below then persists the final clamped
 * value.
 */
function initializeWorkoutControlsPersistence() {
    WORKOUT_CONTROL_IDS.forEach((id) => {
        const input = document.getElementById(id);
        if (!input) return;
        input.addEventListener('input', () => saveWorkoutControls());
        input.addEventListener('change', () => saveWorkoutControls());
    });
}

/**
 * KI-005 criterion 4 (AR-2 / OWNER-1.4) — reset the six controls to the pinned
 * template defaults and drop the stored record. Exported for `clearWorkoutPlan()`.
 *
 * The DOM reset runs under suppression, and the key is removed LAST so it is
 * left ABSENT rather than immediately re-saved as defaults.
 */
export function resetWorkoutControlsToDefaults() {
    withHydrationSuppressed(() => {
        applyWorkoutControlDefaults();
    });
    clearWorkoutControls();
}

export function initializeWorkoutPlanHandlers() {
    // KI-005 hydration ordering (OWNER-1): every save path is suppressed until
    // the stored record has been restored, so initial default population cannot
    // overwrite it, and no listener can replace it before restore has run.
    beginHydration();
    try {
        // Initialize default values
        initializeDefaultValues();

        // Track manual edits to the Weight input so the profile estimate does
        // not overwrite them on subsequent re-applies (Issue #5).
        initializeWeightDirtyTracking();

        // Restore the stored controls over the just-populated template defaults —
        // saved-wins (criterion 8); invalid values fall back per field (criterion 9).
        const { restored } = restoreWorkoutControls();

        // AR-3 ruling: a restored #weight counts as a user edit, so an unrelated
        // profile-estimate re-apply cannot immediately clobber it. Re-using the
        // field's own `input` signal is what `initializeWeightDirtyTracking()`
        // already listens for. A deliberate exercise selection still resets the flag
        // and applies that exercise's recommendation (unchanged behavior).
        if (restored.includes('weight')) {
            document.getElementById('weight')?.dispatchEvent(new Event('input'));
        }

        // Capture listeners go live only now (OWNER-1.2).
        initializeWorkoutControlsPersistence();
    } finally {
        // Correctness cleanup (KI-005): end hydration in `finally` so a throw
        // anywhere above cannot leave `hydrating` stuck true for the page's life,
        // which would silently no-op every subsequent save.
        endHydration();
    }

    // Issue #17 — bind the per-suggestion "show the math" trace expander.
    bindEstimateTraceToggle();

    // Add exercise button handler
    const addExerciseBtn = document.getElementById('add_exercise_btn');
    if (addExerciseBtn) {
        addExerciseBtn.addEventListener('click', handleAddExercise);
    }

    // Handle exercise selection changes
    handleExerciseSelection();
    
    // Handle routine selection changes
    handleRoutineSelection();
    
    // Initialize routine tabs - "All" tab click handler
    initializeRoutineTabs();
    
    // Listen for view mode changes to update muscle display
    document.addEventListener('filterViewModeChanged', handleViewModeChange);

    // Initial fetch of workout plan
    fetchWorkoutPlan();
}
