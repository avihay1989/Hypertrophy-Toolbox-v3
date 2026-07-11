// Workout plan Add Exercise form module (Refactor Plan v3 WP3.4f).
//
// Mechanical feature-split extracted from workout-plan.js: required-field
// validation, submission state/loading feedback, payload submission, and
// default-value initialization. The plan refresh remains orchestration owned
// by workout-plan.js and is injected once at module load to avoid a circular
// import.
import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';
import {
    buildAddExercisePayload,
    clampToAttrRange,
    collectMissingAddFields,
    collectMissingRequiredSelections,
} from './workout-plan-helpers.js';
import {
    applyUserProfileEstimateForSelectedExercise,
    resetWeightUserDirty,
} from './workout-plan-estimates.js';

const addExerciseDeps = {
    refreshPlan: () => {},
};

/**
 * Inject the plan-refresh callback the successful submission path depends on.
 * Called once by workout-plan.js at module load.
 * @param {Partial<typeof addExerciseDeps>} deps
 */
export function configureAddExercise(deps) {
    Object.assign(addExerciseDeps, deps);
}

const WORKOUT_PLAN_DEBUG = false;
const workoutPlanDebugLog = (...args) => {
    if (WORKOUT_PLAN_DEBUG) {
        console.log(...args);
    }
};

let isExerciseSubmissionPending = false;

/**
 * Highlights a required field with validation error styling
 * @param {string} fieldId - The ID of the field to highlight
 * @param {boolean} isInvalid - Whether to add or remove the invalid state
 */
export function setFieldValidationState(fieldId, isInvalid) {
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
        addExerciseDeps.refreshPlan(); // Refresh the table
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

export function initializeDefaultValues() {
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
