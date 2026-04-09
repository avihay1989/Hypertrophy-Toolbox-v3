/**
 * Routine Cascade Selector Module
 * Provides a 3-step cascading dropdown for routine selection:
 * 1. Environment (GYM / Home Workout)
 * 2. Program (Full Body, PPL, Upper Lower, etc.)
 * 3. Routine (Specific workout day)
 */

import { showToast } from './toast.js';

// Routine configuration data structure
const ROUTINE_CONFIG = {
    "GYM": {
        "Full Body": ["Workout A", "Workout B", "Workout C"],
        "Push Pull Legs": ["Push 1", "Pull 1", "Legs 1", "Push 2", "Pull 2", "Legs 2"],
        "Upper Lower": ["Upper 1", "Lower 1", "Upper 2", "Lower 2"],
        "2 Days Split": ["Workout A", "Workout B"],
        "3 Days Split": ["Workout A", "Workout B", "Workout C"],
        "4 Days Split": ["A1", "B1", "A2", "B2"],
        "5 Days Split": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"],
        "6 Days Split": ["Workout A", "Workout B", "Workout C", "Workout D", "Workout E", "Workout F"]
    },
    "Home Workout": {
        "Full Body": ["Workout A", "Workout B", "Workout C"],
        "Push Pull Legs": ["Push 1", "Pull 1", "Legs 1", "Push 2", "Pull 2", "Legs 2"],
        "Upper Lower": ["Upper 1", "Lower 1", "Upper 2", "Lower 2"],
        "2 Days Split": ["Workout A", "Workout B"],
        "3 Days Split": ["Workout A", "Workout B", "Workout C"],
        "4 Days Split": ["A1", "B1", "A2", "B2"],
        "5 Days Split": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"],
        "6 Days Split": ["Workout A", "Workout B", "Workout C", "Workout D", "Workout E", "Workout F"]
    }
};

// Program display order (for consistent ordering)
const PROGRAM_ORDER = [
    "Full Body",
    "Push Pull Legs", 
    "Upper Lower",
    "2 Days Split",
    "3 Days Split",
    "4 Days Split",
    "5 Days Split",
    "6 Days Split"
];

// Module state
let cascadeState = {
    environment: '',
    program: '',
    routine: ''
};

// Stateless mode: always reset routine cascade when page is shown.
let hasPageShowResetListener = false;

/**
 * Initialize the routine cascade selector
 */
export function initializeRoutineCascade() {
    const cascadeContainer = document.getElementById('routine-cascade-container');
    if (!cascadeContainer) return;
    
    // Set up event listeners for cascade dropdowns
    const envSelect = document.getElementById('routine-env');
    const programSelect = document.getElementById('routine-program');
    const routineSelect = document.getElementById('routine-day');
    
    if (envSelect) {
        envSelect.addEventListener('change', handleEnvironmentChange);
    }
    
    if (programSelect) {
        programSelect.addEventListener('change', handleProgramChange);
    }
    
    if (routineSelect) {
        routineSelect.addEventListener('change', handleRoutineChange);
    }

    // Stateless behavior:
    // - Initial load should start blank
    // - Browser back/forward (pageshow) should also reset to blank
    ensurePageShowResetListener();
    applyStatelessCascadeReset();
}

/**
 * Ensure routine cascade is reset whenever the page is shown (including BFCache restores).
 */
function ensurePageShowResetListener() {
    if (hasPageShowResetListener) return;
    window.addEventListener('pageshow', () => {
        applyStatelessCascadeReset();
    });
    hasPageShowResetListener = true;
}

/**
 * Apply stateless reset and notify enhanced dropdown wrappers to sync UI labels.
 */
function applyStatelessCascadeReset() {
    resetCascadeSelector();
    ['routine-env', 'routine-program', 'routine-day'].forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            select.dispatchEvent(new Event('wpdd-rebuild'));
        }
    });
}

/**
 * Handles environment dropdown change
 * @param {Event} e - Change event
 */
function handleEnvironmentChange(e) {
    const environment = e.target.value;
    cascadeState.environment = environment;
    cascadeState.program = '';
    cascadeState.routine = '';
    
    // Clear validation state
    clearCascadeValidation('routine-env');
    
    // Populate program dropdown
    populateProgramDropdown(environment);
    
    // Clear routine dropdown
    clearRoutineDropdown();
    
    // Update the hidden composite field
    updateCompositeRoutineValue();
    
    // Update visual state
    updateCascadeState();
}

/**
 * Handles program dropdown change
 * @param {Event} e - Change event
 */
function handleProgramChange(e) {
    const program = e.target.value;
    cascadeState.program = program;
    cascadeState.routine = '';
    
    // Clear validation state
    clearCascadeValidation('routine-program');
    
    // Populate routine dropdown
    populateRoutineDropdown(cascadeState.environment, program);
    
    // Update the hidden composite field
    updateCompositeRoutineValue();
    
    // Update visual state
    updateCascadeState();
}

/**
 * Handles routine dropdown change
 * @param {Event} e - Change event
 */
function handleRoutineChange(e) {
    const routine = e.target.value;
    cascadeState.routine = routine;
    
    // Clear validation state
    clearCascadeValidation('routine-day');
    
    // Update the hidden composite field
    updateCompositeRoutineValue();
    
    // Update visual state and breadcrumb
    updateCascadeState();
    
    // Trigger the existing routine selection handler
    triggerRoutineSelected();
}

/**
 * Populates the program dropdown based on selected environment
 * @param {string} environment - Selected environment
 */
function populateProgramDropdown(environment) {
    const programSelect = document.getElementById('routine-program');
    if (!programSelect) return;
    
    // Clear current options
    programSelect.innerHTML = '<option value="">Select Program</option>';
    
    if (!environment || !ROUTINE_CONFIG[environment]) {
        programSelect.disabled = true;
        return;
    }
    
    // Get programs for this environment in defined order
    const programs = PROGRAM_ORDER.filter(p => ROUTINE_CONFIG[environment][p]);
    
    programs.forEach(program => {
        const option = document.createElement('option');
        option.value = program;
        option.textContent = program;
        programSelect.appendChild(option);
    });
    
    programSelect.disabled = false;
}

/**
 * Populates the routine dropdown based on selected environment and program
 * @param {string} environment - Selected environment
 * @param {string} program - Selected program
 */
function populateRoutineDropdown(environment, program) {
    const routineSelect = document.getElementById('routine-day');
    if (!routineSelect) return;
    
    // Clear current options
    routineSelect.innerHTML = '<option value="">Select Workout</option>';
    
    if (!environment || !program || !ROUTINE_CONFIG[environment]?.[program]) {
        routineSelect.disabled = true;
        return;
    }
    
    const routines = ROUTINE_CONFIG[environment][program];
    
    routines.forEach(routine => {
        const option = document.createElement('option');
        option.value = routine;
        option.textContent = routine;
        routineSelect.appendChild(option);
    });
    
    routineSelect.disabled = false;
}

/**
 * Clears the routine dropdown
 */
function clearRoutineDropdown() {
    const routineSelect = document.getElementById('routine-day');
    if (!routineSelect) return;
    
    routineSelect.innerHTML = '<option value="">Select Workout</option>';
    routineSelect.disabled = true;
}

/**
 * Updates the hidden composite routine value field
 * Format: "{Environment} - {Program} - {Routine}"
 */
function updateCompositeRoutineValue() {
    const hiddenField = document.getElementById('routine');
    if (!hiddenField) return;
    
    const { environment, program, routine } = cascadeState;
    
    if (environment && program && routine) {
        // Map "Home Workout" to "Home" for the composite value (matching existing data format)
        const envPrefix = environment === "Home Workout" ? "Home" : environment;
        hiddenField.value = `${envPrefix} - ${program} - ${routine}`;
    } else {
        hiddenField.value = '';
    }
    
    // Dispatch change event for any listeners on the hidden field
    hiddenField.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Updates the visual state of the cascade dropdowns
 */
function updateCascadeState() {
    const envSelect = document.getElementById('routine-env');
    const programSelect = document.getElementById('routine-program');
    const routineSelect = document.getElementById('routine-day');
    const breadcrumb = document.getElementById('routine-breadcrumb');
    
    // Update disabled states
    if (programSelect) {
        programSelect.disabled = !cascadeState.environment;
    }
    if (routineSelect) {
        routineSelect.disabled = !cascadeState.program;
    }
    
    // Update visual connector states
    updateConnectorStates();
    
    // Update breadcrumb
    updateBreadcrumb();
}

/**
 * Updates the visual connector arrows between dropdowns
 */
function updateConnectorStates() {
    const connector1 = document.querySelector('.cascade-connector-1');
    const connector2 = document.querySelector('.cascade-connector-2');
    
    if (connector1) {
        connector1.classList.toggle('active', !!cascadeState.environment);
    }
    if (connector2) {
        connector2.classList.toggle('active', !!cascadeState.program);
    }
}

/**
 * Updates the selection breadcrumb display
 */
function updateBreadcrumb() {
    const breadcrumb = document.getElementById('routine-breadcrumb');
    if (!breadcrumb) return;
    
    const { environment, program, routine } = cascadeState;
    
    if (!environment) {
        breadcrumb.innerHTML = '<span class="breadcrumb-placeholder">Select environment to begin</span>';
        breadcrumb.classList.remove('has-selection');
        return;
    }
    
    let parts = [];
    parts.push(`<span class="breadcrumb-env">${environment}</span>`);
    
    if (program) {
        parts.push(`<span class="breadcrumb-separator">→</span>`);
        parts.push(`<span class="breadcrumb-program">${program}</span>`);
    }
    
    if (routine) {
        parts.push(`<span class="breadcrumb-separator">→</span>`);
        parts.push(`<span class="breadcrumb-routine">${routine}</span>`);
    }
    
    breadcrumb.innerHTML = parts.join('');
    breadcrumb.classList.toggle('has-selection', !!routine);
}

/**
 * Triggers the routine selected event for integration with existing code
 */
function triggerRoutineSelected() {
    const hiddenField = document.getElementById('routine');
    if (!hiddenField || !hiddenField.value) return;
    
    // Dispatch a custom event that workout-plan.js can listen to
    const event = new CustomEvent('routineSelected', {
        detail: {
            value: hiddenField.value,
            environment: cascadeState.environment,
            program: cascadeState.program,
            routine: cascadeState.routine
        },
        bubbles: true
    });
    hiddenField.dispatchEvent(event);
}

/**
 * Clears validation error styling from a cascade dropdown
 * @param {string} fieldId - ID of the field to clear
 */
function clearCascadeValidation(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.classList.remove('is-invalid-required');
    const container = field.closest('.cascade-dropdown-wrapper');
    if (container) {
        container.classList.remove('has-validation-error');
    }
}

/**
 * Validates the cascade selection and highlights missing steps
 * @returns {boolean} - True if all steps are selected
 */
export function validateCascadeSelection() {
    const { environment, program, routine } = cascadeState;
    let isValid = true;
    let firstInvalidField = null;
    
    const envSelect = document.getElementById('routine-env');
    const programSelect = document.getElementById('routine-program');
    const routineSelect = document.getElementById('routine-day');
    
    // Validate environment
    if (!environment) {
        if (envSelect) {
            envSelect.classList.add('is-invalid-required');
            envSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
            firstInvalidField = firstInvalidField || envSelect;
        }
        isValid = false;
    }
    
    // Validate program
    if (!program) {
        if (programSelect) {
            programSelect.classList.add('is-invalid-required');
            programSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
            firstInvalidField = firstInvalidField || programSelect;
        }
        isValid = false;
    }
    
    // Validate routine
    if (!routine) {
        if (routineSelect) {
            routineSelect.classList.add('is-invalid-required');
            routineSelect.closest('.cascade-dropdown-wrapper')?.classList.add('has-validation-error');
            firstInvalidField = firstInvalidField || routineSelect;
        }
        isValid = false;
    }
    
    // Focus first invalid field
    if (firstInvalidField) {
        firstInvalidField.focus();
    }
    
    return isValid;
}

/**
 * Resets the cascade selector to initial state
 */
export function resetCascadeSelector() {
    cascadeState = {
        environment: '',
        program: '',
        routine: ''
    };
    
    const envSelect = document.getElementById('routine-env');
    const programSelect = document.getElementById('routine-program');
    const routineSelect = document.getElementById('routine-day');
    
    if (envSelect) envSelect.value = '';
    if (programSelect) {
        programSelect.value = '';
        programSelect.innerHTML = '<option value="">Select Program</option>';
        programSelect.disabled = true;
    }
    if (routineSelect) {
        routineSelect.value = '';
        routineSelect.innerHTML = '<option value="">Select Workout</option>';
        routineSelect.disabled = true;
    }
    
    // Clear hidden field
    updateCompositeRoutineValue();
    
    // Update visual state
    updateCascadeState();
    
    // Clear any validation errors
    clearCascadeValidation('routine-env');
    clearCascadeValidation('routine-program');
    clearCascadeValidation('routine-day');
}

/**
 * Sets the cascade selector to a specific routine value
 * @param {string} compositeValue - Full routine value (e.g., "GYM - Push Pull Legs - Push 1")
 */
export function setCascadeFromComposite(compositeValue) {
    if (!compositeValue) {
        resetCascadeSelector();
        return;
    }
    
    // Parse the composite value
    const parts = compositeValue.split(' - ');
    if (parts.length !== 3) {
        console.warn('Invalid composite routine value:', compositeValue);
        return;
    }
    
    let [env, program, routine] = parts;
    
    // Map "Home" back to "Home Workout" for the dropdown
    if (env === "Home") {
        env = "Home Workout";
    }
    
    // Validate against config
    if (!ROUTINE_CONFIG[env]?.[program]?.includes(routine)) {
        console.warn('Routine not found in config:', compositeValue);
        return;
    }
    
    // Set environment
    const envSelect = document.getElementById('routine-env');
    if (envSelect) {
        envSelect.value = env;
        cascadeState.environment = env;
        populateProgramDropdown(env);
    }
    
    // Set program
    const programSelect = document.getElementById('routine-program');
    if (programSelect) {
        programSelect.value = program;
        cascadeState.program = program;
        populateRoutineDropdown(env, program);
    }
    
    // Set routine
    const routineSelect = document.getElementById('routine-day');
    if (routineSelect) {
        routineSelect.value = routine;
        cascadeState.routine = routine;
    }
    
    // Update hidden field and visual state
    updateCompositeRoutineValue();
    updateCascadeState();
}

/**
 * Gets the current cascade state
 * @returns {Object} Current state with environment, program, routine
 */
export function getCascadeState() {
    return { ...cascadeState };
}

/**
 * Gets the composite routine value
 * @returns {string} Composite routine value or empty string
 */
export function getCompositeRoutineValue() {
    const hiddenField = document.getElementById('routine');
    return hiddenField?.value || '';
}

// Export the config for potential external use
export { ROUTINE_CONFIG, PROGRAM_ORDER };
