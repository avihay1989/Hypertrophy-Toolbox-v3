import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { initializeExerciseImagePreview } from './exercise-image-preview.js';
import { workoutPlanState } from './workout-plan-state.js';
import {
    configureWorkoutPlanTable,
    handleViewModeChange,
    initializeRoutineTabs,
    transformMuscleDisplay,
    updateRoutineTabs,
    updateWorkoutPlanTable,
} from './workout-plan-table.js';
import {
    applyRoutineTabFilter,
    buildSupersetLinkPayload,
    buildSupersetUnlinkPayload,
} from './workout-plan-helpers.js';
import {
    applyUserProfileEstimateForSelectedExercise,
    bindEstimateTraceToggle,
    initializeWeightDirtyTracking,
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

initializeExerciseImagePreview();

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

    // Define default values
    const defaultValues = {
        'sets': '3',
        'min_rep': '6',
        'max_rep_range': '8',
        'rir': '3',
        'weight': '25',  // Default weight is 25
        'rpe': '7'
    };

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
}

function handleExerciseSelection() {
    const exerciseSelect = document.getElementById('exercise');
    if (!exerciseSelect) return;

    exerciseSelect.addEventListener('change', (e) => {
        const selectedExercise = e.target.value;

        // Clear validation error when user selects a valid value
        if (selectedExercise) {
            setFieldValidationState('exercise', false);
            updateExerciseDetails(selectedExercise);
        }
        // Exercise selection is the one-shot trigger that re-applies the
        // profile estimate (Issue #5). Reset the dirty flag so the new
        // estimate overwrites whatever the user typed for the previous
        // exercise.
        resetWeightUserDirty();
        void applyUserProfileEstimateForSelectedExercise();
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

export function initializeWorkoutPlanHandlers() {
    // Initialize default values
    initializeDefaultValues();

    // Track manual edits to the Weight input so the profile estimate does
    // not overwrite them on subsequent re-applies (Issue #5).
    initializeWeightDirtyTracking();

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

/**
 * Handle superset checkbox change
 * @param {HTMLInputElement} checkbox - The checkbox element
 */
function handleSupersetCheckboxChange(checkbox) {
    const exerciseId = parseInt(checkbox.dataset.exerciseId);
    const routine = checkbox.dataset.routine;
    const supersetGroup = checkbox.dataset.supersetGroup;
    const row = checkbox.closest('tr');
    
    if (checkbox.checked) {
        workoutPlanState.selectedExerciseIds.add(exerciseId);
        row.classList.add('superset-selected');
    } else {
        workoutPlanState.selectedExerciseIds.delete(exerciseId);
        row.classList.remove('superset-selected');
    }
    
    updateSupersetActionButtons();
}

/**
 * Update the superset action buttons based on current selection
 */
function updateSupersetActionButtons() {
    const actionsContainer = document.getElementById('superset-actions');
    const linkBtn = document.getElementById('link-superset-btn');
    const unlinkBtn = document.getElementById('unlink-superset-btn');
    const infoSpan = document.getElementById('superset-selection-info');
    
    if (!actionsContainer || !linkBtn || !unlinkBtn || !infoSpan) return;
    
    const selectedCount = workoutPlanState.selectedExerciseIds.size;
    
    if (selectedCount === 0) {
        actionsContainer.style.display = 'none';
        return;
    }
    
    actionsContainer.style.display = 'flex';
    
    // Get selected exercises info
    const selectedCheckboxes = document.querySelectorAll('.superset-checkbox:checked');
    const routines = new Set();
    let hasExistingSuperset = false;
    
    selectedCheckboxes.forEach(cb => {
        routines.add(cb.dataset.routine);
        if (cb.dataset.supersetGroup) {
            hasExistingSuperset = true;
        }
    });
    
    const sameRoutine = routines.size === 1;
    
    // Update info text
    if (selectedCount === 1) {
        if (hasExistingSuperset) {
            infoSpan.textContent = '1 exercise selected (in superset)';
            unlinkBtn.style.display = 'inline-flex';
            linkBtn.style.display = 'none';
        } else {
            infoSpan.textContent = '1 exercise selected - select 1 more to create superset';
            unlinkBtn.style.display = 'none';
            linkBtn.style.display = 'inline-flex';
            linkBtn.disabled = true;
        }
    } else if (selectedCount === 2) {
        if (!sameRoutine) {
            infoSpan.textContent = '⚠️ Exercises must be in the same routine';
            infoSpan.style.color = 'var(--wp-bad)';
            linkBtn.disabled = true;
            unlinkBtn.style.display = 'none';
            linkBtn.style.display = 'inline-flex';
        } else if (hasExistingSuperset) {
            infoSpan.textContent = '⚠️ One or both exercises already in a superset';
            infoSpan.style.color = 'var(--wp-warn)';
            linkBtn.disabled = true;
            unlinkBtn.style.display = 'inline-flex';
            linkBtn.style.display = 'none';
        } else {
            infoSpan.textContent = '2 exercises selected - ready to link';
            infoSpan.style.color = 'var(--wp-good)';
            linkBtn.disabled = false;
            unlinkBtn.style.display = 'none';
            linkBtn.style.display = 'inline-flex';
        }
    } else {
        infoSpan.textContent = `${selectedCount} exercises selected - supersets can only have 2 exercises`;
        infoSpan.style.color = 'var(--wp-warn)';
        linkBtn.disabled = true;
        unlinkBtn.style.display = 'none';
        linkBtn.style.display = 'inline-flex';
    }
}

/**
 * Initialize superset action button click handlers
 */
function initializeSupersetActions() {
    const linkBtn = document.getElementById('link-superset-btn');
    const unlinkBtn = document.getElementById('unlink-superset-btn');
    
    if (linkBtn && !linkBtn.dataset.initialized) {
        linkBtn.addEventListener('click', handleLinkSuperset);
        linkBtn.dataset.initialized = 'true';
    }
    
    if (unlinkBtn && !unlinkBtn.dataset.initialized) {
        unlinkBtn.addEventListener('click', handleUnlinkSuperset);
        unlinkBtn.dataset.initialized = 'true';
    }
}

/**
 * Handle linking selected exercises as a superset
 */
async function handleLinkSuperset() {
    if (workoutPlanState.selectedExerciseIds.size !== 2) {
        showToast('Please select exactly 2 exercises to create a superset', true);
        return;
    }
    
    const exerciseIds = Array.from(workoutPlanState.selectedExerciseIds);
    
    try {
        const data = await api.post('/api/superset/link', buildSupersetLinkPayload(exerciseIds), { showErrorToast: false });
        
        showToast(data.message || 'Superset created successfully');
        // Clear selection and refresh table
        workoutPlanState.selectedExerciseIds.clear();
        document.querySelectorAll('.superset-checkbox:checked').forEach(cb => {
            cb.checked = false;
        });
        // Refresh the workout plan to show updated superset styling
        fetchWorkoutPlan();
    } catch (error) {
        console.error('Error creating superset:', error);
        showToast(error.message || 'Failed to create superset', true);
    }
}

/**
 * Handle unlinking a superset
 */
async function handleUnlinkSuperset() {
    // Get the first selected exercise that's in a superset
    const selectedCheckbox = document.querySelector('.superset-checkbox:checked[data-superset-group]:not([data-superset-group=""])');
    
    if (!selectedCheckbox) {
        showToast('Please select an exercise that is part of a superset', true);
        return;
    }
    
    const exerciseId = parseInt(selectedCheckbox.dataset.exerciseId);
    
    try {
        const data = await api.post('/api/superset/unlink', buildSupersetUnlinkPayload(exerciseId), { showErrorToast: false });
        
        showToast(data.message || 'Superset unlinked successfully');
        // Clear selection and refresh table
        workoutPlanState.selectedExerciseIds.clear();
        document.querySelectorAll('.superset-checkbox:checked').forEach(cb => {
            cb.checked = false;
        });
        // Refresh the workout plan to show updated styling
        fetchWorkoutPlan();
    } catch (error) {
        console.error('Error unlinking superset:', error);
        showToast(error.message || 'Failed to unlink superset', true);
    }
}
