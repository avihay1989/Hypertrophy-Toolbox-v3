import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';
import { initializeExerciseImagePreview } from './exercise-image-preview.js';
import { workoutPlanState } from './workout-plan-state.js';
import {
    configureWorkoutPlanTable,
    handleViewModeChange,
    initializeRoutineTabs,
    transformMuscleDisplay,
    updateCachedExercise,
    updateRoutineTabs,
    updateRowMetadata,
    updateWorkoutPlanTable,
} from './workout-plan-table.js';
import {
    applyRoutineTabFilter,
    buildAddExercisePayload,
    buildExecutionStylePayload,
    buildReplacePayload,
    buildSupersetLinkPayload,
    buildSupersetUnlinkPayload,
    clampToAttrRange,
    collectMissingAddFields,
    collectMissingRequiredSelections,
    resolveSwapErrorToast,
} from './workout-plan-helpers.js';
import {
    applyUserProfileEstimateForSelectedExercise,
    bindEstimateTraceToggle,
    initializeWeightDirtyTracking,
    resetWeightUserDirty,
} from './workout-plan-estimates.js';

initializeExerciseImagePreview();

// Re-export the table renderer so existing importers (and the workout-plan E2E
// harness that imports this module directly) keep resolving it from here.
export { updateWorkoutPlanTable };

// Re-export the profile-estimate entry point so existing importers keep
// resolving it from this module after the WP3.4c estimates split.
export { applyUserProfileEstimateForSelectedExercise };

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

function getSwapButtonLoadingMarkup() {
    return `
        <span class="btn-swap-icon btn-swap-icon--spinner" aria-hidden="true">
            <svg viewBox="0 0 16 16" focusable="false">
                <circle cx="8" cy="8" r="5.25" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" stroke-dasharray="24 12"/>
            </svg>
        </span>
        <span class="btn-swap-label">Swap</span>
    `;
}

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

let isExerciseSubmissionPending = false;

// Execution style state
let executionStyleOptions = null;

/**
 * Fetches execution style options from the API (cached)
 */
async function getExecutionStyleOptions() {
    if (executionStyleOptions) return executionStyleOptions;
    try {
        const response = await api.get('/api/execution_style_options');
        executionStyleOptions = response.data || response;
        return executionStyleOptions;
    } catch (error) {
        console.error('Failed to load execution style options:', error);
        return null;
    }
}

/**
 * Shows execution style picker for an exercise
 * @param {number} exerciseId - The exercise ID
 * @param {Object} currentExercise - Current exercise data from cache
 */
async function showExecutionStylePicker(exerciseId, currentExercise) {
    const options = await getExecutionStyleOptions();
    if (!options) {
        showToast('Failed to load execution style options', true);
        return;
    }
    
    // Remove any existing picker through its own cleanup path so its
    // document-level outside-click listener is detached too
    const existingPicker = document.querySelector('.execution-style-picker');
    if (existingPicker) {
        if (typeof existingPicker._closePicker === 'function') {
            existingPicker._closePicker();
        } else {
            existingPicker.remove();
        }
    }
    
    const currentStyle = currentExercise?.execution_style || 'standard';
    const timeCap = currentExercise?.time_cap_seconds || 60;
    const emomInterval = currentExercise?.emom_interval_seconds || 60;
    const emomRounds = currentExercise?.emom_rounds || 5;
    
    // Create picker element
    const picker = document.createElement('div');
    picker.className = 'execution-style-picker frame-calm-glass';
    picker.innerHTML = `
        <div class="execution-picker-content">
            <div class="execution-picker-header">
                <h6><i class="fas fa-stopwatch me-2"></i>Execution Style</h6>
                <button class="btn-close btn-close-picker" aria-label="Close"></button>
            </div>
            <div class="execution-picker-body">
                <div class="execution-style-options">
                    <label class="execution-option ${currentStyle === 'standard' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="standard" ${currentStyle === 'standard' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-dumbbell"></i></span>
                        <span class="option-text">
                            <strong>Standard</strong>
                            <small>Traditional sets with rest</small>
                        </span>
                    </label>
                    <label class="execution-option ${currentStyle === 'amrap' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="amrap" ${currentStyle === 'amrap' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-stopwatch"></i></span>
                        <span class="option-text">
                            <strong>AMRAP</strong>
                            <small>As Many Reps As Possible</small>
                        </span>
                    </label>
                    <label class="execution-option ${currentStyle === 'emom' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="emom" ${currentStyle === 'emom' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-clock"></i></span>
                        <span class="option-text">
                            <strong>EMOM</strong>
                            <small>Every Minute On the Minute</small>
                        </span>
                    </label>
                </div>
                
                <div class="execution-params amrap-params" style="display: ${currentStyle === 'amrap' ? 'block' : 'none'}">
                    <label class="param-label">
                        <span>Time Cap (seconds)</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="time-cap-${exerciseId}"
                               value="${timeCap}" min="10" max="600" step="5">
                    </label>
                </div>
                
                <div class="execution-params emom-params" style="display: ${currentStyle === 'emom' ? 'block' : 'none'}">
                    <label class="param-label">
                        <span>Interval (seconds)</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="emom-interval-${exerciseId}"
                               value="${emomInterval}" min="15" max="180" step="5">
                    </label>
                    <label class="param-label">
                        <span>Rounds</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="emom-rounds-${exerciseId}"
                               value="${emomRounds}" min="1" max="20">
                    </label>
                </div>
            </div>
            <div class="execution-picker-footer">
                <button class="btn btn-sm btn-outline-secondary btn-calm-ghost btn-cancel-exec">Cancel</button>
                <button class="btn btn-sm btn-primary btn-calm-primary btn-save-exec" data-exercise-id="${exerciseId}">
                    <i class="fas fa-check me-1"></i>Apply
                </button>
            </div>
        </div>
    `;
    
    // Position picker near the clicked cell
    const cell = document.querySelector(`.execution-style-cell[data-exercise-id="${exerciseId}"]`);
    document.body.appendChild(picker);
    
    if (cell) {
        const rect = cell.getBoundingClientRect();
        const pickerHeight = picker.offsetHeight || 350; // Estimated height if not yet rendered
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        
        picker.style.position = 'fixed';
        picker.style.left = `${Math.max(10, rect.left - 100)}px`;
        picker.style.zIndex = '1050';
        
        // Position above if not enough space below, otherwise position below
        if (spaceBelow < pickerHeight && spaceAbove > spaceBelow) {
            picker.style.bottom = `${viewportHeight - rect.top + 5}px`;
            picker.style.top = 'auto';
            picker.classList.add('picker-dropup');
        } else {
            picker.style.top = `${rect.bottom + 5}px`;
            picker.style.bottom = 'auto';
        }
    }
    
    // Single close path — every way of dismissing the picker (Close, Cancel,
    // Save, outside click, replacement by a newly opened picker) must go
    // through closePicker() so the document-level outside-click listener
    // never outlives the picker element.
    let outsideClickTimer = null;
    const closeOnOutside = (e) => {
        if (!picker.contains(e.target) && !e.target.closest('.execution-style-cell')) {
            closePicker();
        }
    };
    const closePicker = () => {
        clearTimeout(outsideClickTimer);
        document.removeEventListener('click', closeOnOutside);
        picker.remove();
    };
    picker._closePicker = closePicker;

    // Event listeners
    const radios = picker.querySelectorAll('input[type="radio"]');
    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            picker.querySelectorAll('.execution-option').forEach(opt => opt.classList.remove('active'));
            radio.closest('.execution-option').classList.add('active');
            
            const style = radio.value;
            picker.querySelector('.amrap-params').style.display = style === 'amrap' ? 'block' : 'none';
            picker.querySelector('.emom-params').style.display = style === 'emom' ? 'block' : 'none';
        });
    });
    
    picker.querySelector('.btn-close-picker').addEventListener('click', () => closePicker());
    picker.querySelector('.btn-cancel-exec').addEventListener('click', () => closePicker());
    
    picker.querySelector('.btn-save-exec').addEventListener('click', async () => {
        const selectedStyle = picker.querySelector(`input[name="exec-style-${exerciseId}"]:checked`).value;
        const timeCap = parseInt(picker.querySelector(`#time-cap-${exerciseId}`).value);
        const emomInterval = parseInt(picker.querySelector(`#emom-interval-${exerciseId}`).value);
        const emomRounds = parseInt(picker.querySelector(`#emom-rounds-${exerciseId}`).value);
        const payload = buildExecutionStylePayload(exerciseId, selectedStyle, { timeCap, emomInterval, emomRounds });
        
        try {
            const result = await api.post('/api/execution_style', payload);
            showToast(`Execution style set to ${selectedStyle.toUpperCase()}`);
            closePicker();
            // Refresh the workout plan to show updated badge
            await fetchWorkoutPlan();
        } catch (error) {
            showToast(error.message || 'Failed to update execution style', true);
        }
    });
    
    // Close on outside click (delayed so the click that opened the picker
    // does not immediately close it). closePicker() cancels this timer if the
    // picker is dismissed before the listener is ever attached.
    outsideClickTimer = setTimeout(() => {
        document.addEventListener('click', closeOnOutside);
    }, 100);
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

/**
 * Highlights a required field with validation error styling
 * @param {string} fieldId - The ID of the field to highlight
 * @param {boolean} isInvalid - Whether to add or remove the invalid state
 */
function setFieldValidationState(fieldId, isInvalid) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    // Find the parent container for label highlighting
    const container = field.closest('.selection-field') || field.closest('.col-lg-6') || field.closest('.col-12');
    
    // Check if there's an enhanced dropdown wrapper
    const wpddContainer = field.closest('.wpdd');
    
    // Check if this is the hidden routine field (for cascade selector)
    const isCascadeRoutine = fieldId === 'routine' && field.type === 'hidden';
    
    if (isInvalid) {
        if (isCascadeRoutine) {
            // For cascade selector, highlight all incomplete dropdowns
            highlightIncompleteCascadeDropdowns();
        } else {
            // Add invalid class to the native select (for non-enhanced state)
            field.classList.add('is-invalid-required');
            
            // Add invalid class to enhanced dropdown container if it exists
            if (wpddContainer) {
                wpddContainer.classList.add('is-invalid-required');
            }
            
            // Highlight the parent container/label
            if (container) {
                container.classList.add('has-validation-error');
            }
        }
    } else {
        if (isCascadeRoutine) {
            // Clear cascade dropdown validation
            clearCascadeDropdownValidation();
        } else {
            // Remove invalid classes
            field.classList.remove('is-invalid-required');
            
            if (wpddContainer) {
                wpddContainer.classList.remove('is-invalid-required');
            }
            
            if (container) {
                container.classList.remove('has-validation-error');
            }
        }
    }
}

/**
 * Highlights incomplete cascade dropdowns
 */
function highlightIncompleteCascadeDropdowns() {
    const envSelect = document.getElementById('routine-env');
    const programSelect = document.getElementById('routine-program');
    const routineSelect = document.getElementById('routine-day');
    
    // Check which dropdowns are incomplete and highlight them
    if (envSelect && !envSelect.value) {
        envSelect.classList.add('is-invalid-required');
        envSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
        envSelect.focus();
    } else if (programSelect && !programSelect.value) {
        programSelect.classList.add('is-invalid-required');
        programSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
        programSelect.focus();
    } else if (routineSelect && !routineSelect.value) {
        routineSelect.classList.add('is-invalid-required');
        routineSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
        routineSelect.focus();
    }
}

/**
 * Clears validation from cascade dropdowns
 */
function clearCascadeDropdownValidation() {
    const cascadeDropdowns = ['routine-env', 'routine-program', 'routine-day'];
    cascadeDropdowns.forEach(id => {
        const dropdown = document.getElementById(id);
        if (dropdown) {
            dropdown.classList.remove('is-invalid-required');
            dropdown.closest('.cascade-dropdown-wrapper')?.classList.remove('has-validation-error');
        }
    });
}

/**
 * Clears validation error highlighting from Routine and Exercise fields
 */
function clearRequiredFieldValidation() {
    setFieldValidationState('routine', false);
    setFieldValidationState('exercise', false);
}

/**
 * Validates required selection fields (Routine and Exercise) and highlights missing ones
 * @returns {boolean} - True if validation passes, false if fields are missing
 */
function validateRequiredSelections() {
    const routineSelect = document.getElementById('routine');
    const exerciseSelect = document.getElementById('exercise');
    
    const routine = routineSelect?.value;
    const exercise = exerciseSelect?.value;
    
    let isValid = true;
    let firstInvalidField = null;
    
    // Validate Routine (required)
    if (!routine) {
        setFieldValidationState('routine', true);
        isValid = false;
        firstInvalidField = firstInvalidField || routineSelect;
    } else {
        setFieldValidationState('routine', false);
    }
    
    // Validate Exercise (required)
    if (!exercise) {
        setFieldValidationState('exercise', true);
        isValid = false;
        // Only focus exercise if routine is already selected
        if (routine) {
            firstInvalidField = firstInvalidField || exerciseSelect;
        }
    } else {
        setFieldValidationState('exercise', false);
    }
    
    // Focus the first invalid field (prioritize routine)
    if (firstInvalidField) {
        // For enhanced dropdowns, click the button to open it
        const wpddContainer = firstInvalidField.closest('.wpdd');
        if (wpddContainer) {
            const wpddButton = wpddContainer.querySelector('.wpdd-button');
            if (wpddButton) {
                wpddButton.focus();
            }
        } else {
            firstInvalidField.focus();
        }
    }
    
    return isValid;
}

export function handleAddExercise(e) {
    if (e) e.preventDefault();

    if (isExerciseSubmissionPending) {
        return;
    }
    
    // First, validate required selection fields (Routine and Exercise) with visual feedback
    if (!validateRequiredSelections()) {
        // Show toast for missing required selection fields
        const routine = document.getElementById('routine')?.value;
        const exercise = document.getElementById('exercise')?.value;
        
        const missingSelections = collectMissingRequiredSelections(routine, exercise);
        
        if (missingSelections.length > 0) {
            showToast(`Please select: ${missingSelections.join(' and ')}`, true);
            return;
        }
    }
    
    // Get all required form values
    const exercise = document.getElementById('exercise')?.value;
    const routine = document.getElementById('routine')?.value;
    const sets = document.getElementById('sets')?.value;
    const minRepRange = document.getElementById('min_rep')?.value;
    const maxRepRange = document.getElementById('max_rep_range')?.value;
    const rir = document.getElementById('rir')?.value;
    const weight = document.getElementById('weight')?.value;
    const rpe = document.getElementById('rpe')?.value;

    // Detailed validation
    const missingFields = collectMissingAddFields({ exercise, routine, sets, minRepRange, maxRepRange, weight });

    if (missingFields.length > 0) {
        const message = `Please fill in the following required fields: ${missingFields.join(', ')}`;
            workoutPlanDebugLog('Validation failed:', message);
            workoutPlanDebugLog('Current form values:', { exercise, routine, sets, minRepRange, maxRepRange, weight });
        showToast(message, true);
        return;
    }

    // Prepare exercise data
    const exerciseData = buildAddExercisePayload({ exercise, routine, sets, minRepRange, maxRepRange, rir, weight, rpe });

    workoutPlanDebugLog('Sending exercise data:', exerciseData);
    void sendExerciseData(exerciseData);
}

function setAddExerciseButtonLoading(isLoading) {
    const addExerciseBtn = document.getElementById('add_exercise_btn');
    if (!addExerciseBtn) {
        return;
    }

    if (!addExerciseBtn.dataset.defaultHtml) {
        addExerciseBtn.dataset.defaultHtml = addExerciseBtn.innerHTML;
    }

    addExerciseBtn.disabled = isLoading;
    addExerciseBtn.classList.toggle('loading', isLoading);
    addExerciseBtn.setAttribute('aria-busy', String(isLoading));
    addExerciseBtn.innerHTML = isLoading
        ? '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Adding...'
        : addExerciseBtn.dataset.defaultHtml;
}

async function sendExerciseData(exerciseData) {
    if (isExerciseSubmissionPending) {
        return;
    }

    isExerciseSubmissionPending = true;
    setAddExerciseButtonLoading(true);

    try {
        const data = await api.post('/add_exercise', exerciseData, { showErrorToast: false });
        const message = data.message || data.data?.message || 'Exercise added successfully';
        
        showToast('success', message);
        const addBtn = document.getElementById('add_exercise_btn');
        if (addBtn) {
            addBtn.classList.add('is-success');
            setTimeout(() => addBtn.classList.remove('is-success'), 1000);
        }
        fetchWorkoutPlan(); // Refresh the table
        notifyVolumeAffectingPlanChange('add-exercise');
        resetFormFields();
    } catch (error) {
        logApiError('Error adding exercise:', error);
        showToast(isHandledApiError(error) ? 'warning' : 'error', error.message || 'Failed to add exercise');
    } finally {
        isExerciseSubmissionPending = false;
        setAddExerciseButtonLoading(false);
    }
}

function resetFormFields() {
    resetWeightUserDirty();
    void applyUserProfileEstimateForSelectedExercise();
}

function initializeDefaultValues() {
    const defaultValues = {
        'weight': 25,
        'sets': 3,
        'rir': 3,
        'rpe': 7,
        'min_rep': 6,
        'max_rep_range': 8
    };

    // Set default values for each input field
    Object.entries(defaultValues).forEach(([id, value]) => {
        const input = document.getElementById(id);
        if (input) {
            input.value = value;

            // Clamp to min/max on commit (blur / Enter). Using `change`
            // instead of `input` so we don't overwrite mid-typing — that
            // previously stripped decimals (parseInt) and snapped a
            // momentarily-empty field to a hardcoded default.
            input.addEventListener('change', function() {
                if (this.value === '') return;
                const minAttr = this.getAttribute('min');
                const maxAttr = this.getAttribute('max');
                const parsed = parseFloat(this.value);
                if (Number.isNaN(parsed)) return;
                const clamped = clampToAttrRange(parsed, minAttr, maxAttr);
                if (clamped !== parsed) {
                    this.value = clamped;
                }
            });
        }
    });
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

/**
 * Handles the swap/replace exercise action
 * @param {number} exerciseId - The user_selection.id of the exercise to swap
 * @param {string} currentExerciseName - The current exercise name (for display)
 */
async function handleSwapExercise(exerciseId, currentExerciseName) {
    const row = document.querySelector(`tr[data-exercise-id="${exerciseId}"]`);
    const swapBtn = row?.querySelector('.btn-swap');
    
    if (!row || !swapBtn) {
        console.error('Could not find row or swap button for exercise:', exerciseId);
        return;
    }
    
    // Disable button and show loading state
    swapBtn.disabled = true;
    const originalIcon = swapBtn.innerHTML;
    swapBtn.innerHTML = getSwapButtonLoadingMarkup();
    swapBtn.classList.add('loading');
    
    try {
        const data = await api.post('/replace_exercise', buildReplacePayload(exerciseId), { showLoading: false, showErrorToast: false }); // We handle our own loading state
        
        // api wrapper returns raw response, check if we got updated_row
        const responseData = data.data || data;
        
        if (responseData?.updated_row) {
            // Success - update the row in place
            const updatedRow = responseData.updated_row;
            const oldExercise = responseData.old_exercise;
            const newExercise = responseData.new_exercise;
            
            // Update the exercise name in the cell
            const exerciseNameSpan = row.querySelector('.exercise-name');
            if (exerciseNameSpan) {
                exerciseNameSpan.textContent = newExercise;
            }
            
            // Update other metadata cells
            updateRowMetadata(row, updatedRow);
            
            // Update the cached data
            updateCachedExercise(exerciseId, updatedRow);
            
            // Show success toast with remaining options count
            const remaining = responseData.remaining_options ?? 0;
            const optionsText = remaining === 1 ? '1 option left' : `${remaining} options left`;
            showToast('success', `Replaced "${oldExercise}" → "${newExercise}" (${optionsText})`);
            notifyVolumeAffectingPlanChange('replace-exercise');
            
            // Brief highlight effect on the row
            row.classList.add('row-swapped');
            setTimeout(() => row.classList.remove('row-swapped'), 2000);
            
        } else {
            // Handle specific error reasons
            const reason = responseData?.error?.reason || 'unknown';
            const message = responseData?.error?.message || responseData?.message || 'Failed to replace exercise';
            
            const t = resolveSwapErrorToast(reason, message);
            showToast(t.severity, t.message);
        }
        
    } catch (error) {
        console.error('Error swapping exercise:', error);
        // Handle specific error reasons from the error object
        const reason = error?.reason || 'unknown';
        const message = error?.message || 'Failed to replace exercise. Please try again.';
        
        const t = resolveSwapErrorToast(reason, message);
        showToast(t.severity, t.message);
    } finally {
        // Restore button state
        swapBtn.disabled = false;
        swapBtn.innerHTML = originalIcon;
        swapBtn.classList.remove('loading');
    }
}
