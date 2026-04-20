import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';

/**
 * Transform muscle display value based on current view mode (Simple/Advanced)
 * @param {string} value - Raw muscle value from database
 * @param {'primary'|'isolated'} type - Type of muscle field
 * @param {string} isolatedMuscles - Optional isolated muscles for this exercise (for scientific detail)
 * @returns {string} - Display value appropriate for current mode
 */
function transformMuscleDisplay(value, type = 'primary', isolatedMuscles = null) {
    if (!value || value === 'N/A') return value || 'N/A';
    
    // Check if FilterViewMode is available
    if (typeof window.FilterViewMode === 'undefined') {
        return value;
    }
    
    if (type === 'isolated') {
        return window.FilterViewMode.transformIsolatedMuscleDisplay(value);
    }
    
    // In scientific mode, try to show isolated muscle detail for primary muscle
    const mode = window.FilterViewMode.getViewMode();
    if (mode === 'advanced' && isolatedMuscles && type === 'primary') {
        // Parse the isolated muscles and find ones related to this muscle group
        const relevantIsolated = getRelevantIsolatedMuscles(value, isolatedMuscles);
        if (relevantIsolated) {
            return relevantIsolated;
        }
    }
    
    return window.FilterViewMode.transformMuscleDisplay(value);
}

/**
 * Get isolated muscles that relate to a given muscle group
 * Maps primary muscle groups to their isolated muscle patterns
 */
function getRelevantIsolatedMuscles(muscleGroup, isolatedMusclesStr) {
    if (!isolatedMusclesStr) return null;
    
    // Map muscle groups to patterns that match their isolated muscles
    const muscleGroupPatterns = {
        'Chest': ['pectoralis', 'pec'],
        'Biceps': ['bicep'],
        'Triceps': ['tricep'],
        'Front-Shoulder': ['anterior-deltoid'],
        'Middle-Shoulder': ['lateral-deltoid'],
        'Rear-Shoulder': ['posterior-deltoid'],
        'Quadriceps': ['quadricep', 'rectus-femoris', 'inner-thigh'],
        'Hamstrings': ['hamstring'],
        'Gluteus Maximus': ['gluteus'],
        'Calves': ['soleus', 'gastrocnemius', 'tibialis'],
        'Latissimus Dorsi': ['lat'],
        'Trapezius': ['trapezius'],
        'Forearms': ['wrist-'],
        'Abs/Core': ['abdominal'],
    };
    
    const patterns = muscleGroupPatterns[muscleGroup];
    if (!patterns) return null;
    
    // Split isolated muscles and find matching ones
    const isolatedList = isolatedMusclesStr.split(',').map(m => m.trim().toLowerCase());
    const matches = isolatedList.filter(muscle => 
        patterns.some(pattern => muscle.includes(pattern))
    );
    
    if (matches.length === 0) return null;
    
    // Transform each match to proper label
    return matches.map(m => {
        // Use FilterViewMode to get the proper label
        if (window.FilterViewMode?.ADVANCED_MUSCLES?.[m]) {
            return window.FilterViewMode.ADVANCED_MUSCLES[m].label;
        }
        // Fallback: titlecase
        return m.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }).join(', ');
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

// Module-level state for routine tabs
let currentRoutineTabFilter = 'all';
let allExercisesCache = [];
let isExerciseSubmissionPending = false;

// Superset selection state
let selectedExerciseIds = new Set();
let supersetColorMap = new Map(); // Maps superset_group to color index (1-4)

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
 * Renders an execution style badge for an exercise
 * @param {Object} exercise - The exercise object
 * @returns {string} HTML string for the badge
 */
function renderExecutionStyleBadge(exercise) {
    const style = exercise.execution_style || 'standard';
    const timeCap = exercise.time_cap_seconds;
    const emomInterval = exercise.emom_interval_seconds;
    const emomRounds = exercise.emom_rounds;
    
    let badgeClass = 'execution-badge';
    let icon = '';
    let label = '';
    let details = '';
    
    switch (style) {
        case 'amrap':
            badgeClass += ' execution-badge--amrap';
            icon = '<i class="fas fa-stopwatch"></i>';
            label = 'AMRAP';
            if (timeCap) {
                details = `<span class="execution-details">${timeCap}s</span>`;
            }
            break;
        case 'emom':
            badgeClass += ' execution-badge--emom';
            icon = '<i class="fas fa-clock"></i>';
            label = 'EMOM';
            if (emomInterval && emomRounds) {
                details = `<span class="execution-details">${emomRounds}×${emomInterval}s</span>`;
            }
            break;
        default:
            badgeClass += ' execution-badge--standard';
            icon = '<i class="fas fa-dumbbell"></i>';
            label = 'STD';
    }
    
    return `<button class="btn ${badgeClass}" aria-label="Click to change execution style">
        ${icon} <span class="execution-label">${label}</span>${details}
    </button>`;
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
    
    // Remove any existing picker
    const existingPicker = document.querySelector('.execution-style-picker');
    if (existingPicker) existingPicker.remove();
    
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
    
    picker.querySelector('.btn-close-picker').addEventListener('click', () => picker.remove());
    picker.querySelector('.btn-cancel-exec').addEventListener('click', () => picker.remove());
    
    picker.querySelector('.btn-save-exec').addEventListener('click', async () => {
        const selectedStyle = picker.querySelector(`input[name="exec-style-${exerciseId}"]:checked`).value;
        const payload = {
            exercise_id: exerciseId,
            execution_style: selectedStyle
        };
        
        if (selectedStyle === 'amrap') {
            payload.time_cap_seconds = parseInt(picker.querySelector(`#time-cap-${exerciseId}`).value) || 60;
        } else if (selectedStyle === 'emom') {
            payload.emom_interval_seconds = parseInt(picker.querySelector(`#emom-interval-${exerciseId}`).value) || 60;
            payload.emom_rounds = parseInt(picker.querySelector(`#emom-rounds-${exerciseId}`).value) || 5;
        }
        
        try {
            const result = await api.post('/api/execution_style', payload);
            showToast(`Execution style set to ${selectedStyle.toUpperCase()}`);
            picker.remove();
            // Refresh the workout plan to show updated badge
            await fetchWorkoutPlan();
        } catch (error) {
            showToast(error.message || 'Failed to update execution style', true);
        }
    });
    
    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closeOnOutside(e) {
            if (!picker.contains(e.target) && !e.target.closest('.execution-style-cell')) {
                picker.remove();
                document.removeEventListener('click', closeOnOutside);
            }
        });
    }, 100);
}

/**
 * Parses a routine string in "Environment - Program - Workout" format
 * @param {string} routine - The routine string to parse
 * @returns {Object} Object with env, program, workout properties
 */
function parseRoutine(routine) {
    if (!routine) return { env: '', program: '', workout: '' };
    const parts = routine.split(' - ').map(p => p.trim());
    return {
        env: parts[0] || '',
        program: parts[1] || '',
        workout: parts[2] || ''
    };
}

/**
 * Formats a routine string for display in 3 lines (Environment, Program, Workout)
 * @param {string} routine - The routine string to format
 * @returns {string} HTML string with routine formatted on 3 lines
 */
function formatRoutineForDisplay(routine) {
    if (!routine) return 'N/A';
    const parsed = parseRoutine(routine);
    if (!parsed.env && !parsed.program && !parsed.workout) return 'N/A';
    return `<span class="routine-env">${parsed.env || ''}</span><span class="routine-program">${parsed.program || ''}</span><span class="routine-workout">${parsed.workout || ''}</span>`;
}

/**
 * Formats a routine string for display in tab labels (3 lines)
 * @param {string} routine - The routine string to format
 * @returns {string} HTML string with routine formatted on 3 lines for tabs
 */
function formatRoutineForTab(routine) {
    if (!routine) return 'N/A';
    const parsed = parseRoutine(routine);
    if (!parsed.env && !parsed.program && !parsed.workout) return routine;
    return `<span class="tab-env">${parsed.env || ''}</span><span class="tab-program">${parsed.program || ''}</span><span class="tab-workout">${parsed.workout || ''}</span>`;
}

/**
 * Compares two routine strings for sorting
 * Sorts by Environment, then Program, then Workout
 * @param {string} a - First routine
 * @param {string} b - Second routine
 * @returns {number} Comparison result (-1, 0, or 1)
 */
function compareRoutines(a, b) {
    const parsedA = parseRoutine(a);
    const parsedB = parseRoutine(b);
    
    // Compare environment first
    if (parsedA.env !== parsedB.env) {
        return parsedA.env.localeCompare(parsedB.env);
    }
    // Then compare program
    if (parsedA.program !== parsedB.program) {
        return parsedA.program.localeCompare(parsedB.program);
    }
    // Finally compare workout
    return parsedA.workout.localeCompare(parsedB.workout);
}

// Workout plan functionality
export async function fetchWorkoutPlan() {
    try {
        const data = await api.get('/get_workout_plan');
        
        // api wrapper returns the response data directly (from data.data if standardized)
        const exercises = data.data !== undefined ? data.data : data;
        
        // Cache all exercises for tab filtering
        allExercisesCache = exercises;
        
        // Update routine tabs based on available routines
        updateRoutineTabs(exercises);
        
        // Apply current tab filter and render
        const filteredExercises = applyRoutineTabFilter(exercises, currentRoutineTabFilter);
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

/**
 * Updates the routine tabs based on available routines in the data
 * @param {Array} exercises - Array of exercise objects
 */
function updateRoutineTabs(exercises) {
    const tabsContainer = document.getElementById('routine-tabs');
    if (!tabsContainer) return;
    
    // Get unique routines and count exercises per routine
    const routineCounts = {};
    exercises.forEach(ex => {
        const routine = ex.routine || 'Unknown';
        routineCounts[routine] = (routineCounts[routine] || 0) + 1;
    });
    
    // Sort routines by Environment > Program > Workout for consistent ordering
    const sortedRoutines = Object.keys(routineCounts).sort(compareRoutines);
    
    // Update "All" tab count
    const allCountEl = document.getElementById('tab-count-all');
    if (allCountEl) {
        allCountEl.textContent = exercises.length;
    }
    
    // Remove existing dynamic tabs (keep the "All" tab)
    const existingDynamicTabs = tabsContainer.querySelectorAll('.routine-tab[data-dynamic="true"]');
    existingDynamicTabs.forEach(tab => tab.remove());
    
    // Create tabs for each routine
    sortedRoutines.forEach(routine => {
        const tabId = `tab-${routine.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`;
        
        const tabLi = document.createElement('li');
        tabLi.className = 'routine-tab';
        tabLi.setAttribute('data-dynamic', 'true');
        tabLi.setAttribute('role', 'presentation');
        
        const tabBtn = document.createElement('button');
        tabBtn.className = 'routine-tab-btn';
        tabBtn.setAttribute('data-routine', routine);
        tabBtn.setAttribute('role', 'tab');
        tabBtn.setAttribute('aria-selected', 'false');
        tabBtn.setAttribute('aria-controls', 'workout_plan_table_body');
        tabBtn.setAttribute('id', tabId);
        
        // Mark as active if this is the currently selected tab
        if (routine === currentRoutineTabFilter) {
            tabBtn.classList.add('active');
            tabBtn.setAttribute('aria-selected', 'true');
            // Also remove active from "All" tab
            const allTab = tabsContainer.querySelector('[data-routine="all"]');
            if (allTab) {
                allTab.classList.remove('active');
                allTab.setAttribute('aria-selected', 'false');
            }
        }
        
        tabBtn.innerHTML = `
            <span class="tab-label">${formatRoutineForTab(routine)}</span>
            <span class="tab-count">${routineCounts[routine]}</span>
        `;
        
        tabBtn.addEventListener('click', () => handleRoutineTabClick(routine));
        
        tabLi.appendChild(tabBtn);
        tabsContainer.appendChild(tabLi);
    });
    
    // If current filter is "all", ensure the "All" tab is active
    if (currentRoutineTabFilter === 'all') {
        const allTabBtn = tabsContainer.querySelector('[data-routine="all"]');
        if (allTabBtn) {
            allTabBtn.classList.add('active');
            allTabBtn.setAttribute('aria-selected', 'true');
        }
    }
    
    // If the current filter's routine no longer exists, reset to "all"
    if (currentRoutineTabFilter !== 'all' && !sortedRoutines.includes(currentRoutineTabFilter)) {
        currentRoutineTabFilter = 'all';
        const allTabBtn = tabsContainer.querySelector('[data-routine="all"]');
        if (allTabBtn) {
            allTabBtn.classList.add('active');
            allTabBtn.setAttribute('aria-selected', 'true');
        }
    }
}

/**
 * Handles routine tab click events
 * @param {string} routine - The routine name or 'all'
 */
function handleRoutineTabClick(routine) {
    const tabsContainer = document.getElementById('routine-tabs');
    if (!tabsContainer) return;
    
    // Update active state on all tabs
    tabsContainer.querySelectorAll('.routine-tab-btn').forEach(btn => {
        const isTarget = btn.getAttribute('data-routine') === routine;
        btn.classList.toggle('active', isTarget);
        btn.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    });
    
    // Update current filter
    currentRoutineTabFilter = routine;
    
    // Apply filter and re-render table
    const filteredExercises = applyRoutineTabFilter(allExercisesCache, routine);
    updateWorkoutPlanTable(filteredExercises);
}

/**
 * Filters exercises by routine
 * @param {Array} exercises - Array of exercise objects
 * @param {string} routineFilter - The routine to filter by, or 'all'
 * @returns {Array} Filtered exercises
 */
function applyRoutineTabFilter(exercises, routineFilter) {
    if (routineFilter === 'all') {
        return exercises;
    }
    return exercises.filter(ex => ex.routine === routineFilter);
}

/**
 * Gets the current routine tab filter value (for external modules if needed)
 * @returns {string} Current routine filter
 */
export function getCurrentRoutineTabFilter() {
    return currentRoutineTabFilter;
}

/**
 * Resets the routine tab filter to 'all' (for external modules if needed)
 */
export function resetRoutineTabFilter() {
    currentRoutineTabFilter = 'all';
    const tabsContainer = document.getElementById('routine-tabs');
    if (tabsContainer) {
        tabsContainer.querySelectorAll('.routine-tab-btn').forEach(btn => {
            const isAll = btn.getAttribute('data-routine') === 'all';
            btn.classList.toggle('active', isAll);
            btn.setAttribute('aria-selected', isAll ? 'true' : 'false');
        });
    }
}

    const WORKOUT_PLAN_DEBUG = false;
    const workoutPlanDebugLog = (...args) => {
        if (WORKOUT_PLAN_DEBUG) {
            console.log(...args);
        }
    };
export function reloadWorkoutPlan(data) {
    const workoutTable = document.querySelector("#workout-plan-table tbody");
    if (!workoutTable) {
        console.error("Workout plan table not found in the DOM");
        return;
    }

    // Clear existing rows
    workoutTable.innerHTML = "";

    // Add all exercises to the table
    data.forEach((item) => {
        if (!item.id) {
            console.error("Missing ID for exercise:", item);
            return;
        }

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.id}</td>
            <td>${item.routine || "N/A"}</td>
            <td>${item.exercise || "N/A"}</td>
            <td>${transformMuscleDisplay(item.primary_muscle_group, 'primary', item.advanced_isolated_muscles)}</td>
            <td>${transformMuscleDisplay(item.secondary_muscle_group, 'primary', item.advanced_isolated_muscles)}</td>
            <td>${transformMuscleDisplay(item.tertiary_muscle_group, 'primary', item.advanced_isolated_muscles)}</td>
            <td>${transformMuscleDisplay(item.advanced_isolated_muscles, 'isolated')}</td>
            <td>${item.utility || "N/A"}</td>
            <td>${item.sets || "N/A"}</td>
            <td>${item.min_rep_range || "N/A"}</td>
            <td>${item.max_rep_range || "N/A"}</td>
            <td>${item.rir || "N/A"}</td>
            <td>${item.rpe !== null ? item.rpe : "N/A"}</td>
            <td>${item.weight || "N/A"}</td>
            <td>${item.grips || "N/A"}</td>
            <td>${item.stabilizers || "N/A"}</td>
            <td>${item.synergists || "N/A"}</td>
            <td>
                <button class="btn btn-danger btn-sm text-white btn-calm-danger" onclick="removeExercise(${item.id})">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </td>`;
        workoutTable.appendChild(row);
    });
}

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

export function handleExerciseSelection() {
    const exerciseSelect = document.getElementById('exercise');
    if (!exerciseSelect) return;

    exerciseSelect.addEventListener('change', (e) => {
        const selectedExercise = e.target.value;
        
        // Clear validation error when user selects a valid value
        if (selectedExercise) {
            setFieldValidationState('exercise', false);
            updateExerciseDetails(selectedExercise);
            // Note: updateExerciseForm is NOT called here to preserve user-entered
            // workout control values (weight, sets, RIR, etc.). The controls are
            // only reset after clicking "Add Exercise" in sendExerciseData().
        }
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
        
        const missingSelections = [];
        if (!routine) missingSelections.push('Routine');
        if (!exercise) missingSelections.push('Exercise');
        
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
    const missingFields = [];
    if (!exercise) missingFields.push('Exercise');
    if (!routine) missingFields.push('Routine');
    if (!sets) missingFields.push('Sets');
    if (!minRepRange) missingFields.push('Min Rep Range');
    if (!maxRepRange) missingFields.push('Max Rep Range');
    if (!weight) missingFields.push('Weight');

    if (missingFields.length > 0) {
        const message = `Please fill in the following required fields: ${missingFields.join(', ')}`;
            workoutPlanDebugLog('Validation failed:', message);
            workoutPlanDebugLog('Current form values:', { exercise, routine, sets, minRepRange, maxRepRange, weight });
        showToast(message, true);
        return;
    }

    // Prepare exercise data
    const exerciseData = {
        exercise: exercise,
        routine: routine,
        sets: parseInt(sets),
        min_rep_range: parseInt(minRepRange),
        max_rep_range: parseInt(maxRepRange),
        rir: parseInt(rir || 0),
        weight: parseFloat(weight),
        rpe: rpe ? parseFloat(rpe) : null
    };

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
    // Preserve the current routine and exercise
    const currentRoutine = document.getElementById('routine').value;
    const currentExercise = document.getElementById('exercise').value;
    
    // Reset form fields to default values
    document.getElementById('sets').value = '3';
    document.getElementById('rir').value = '3';
    document.getElementById('weight').value = '25';
    document.getElementById('min_rep').value = '6';
    document.getElementById('max_rep_range').value = '8';
    document.getElementById('rpe').value = '7';

    // Restore the routine and exercise
    if (currentRoutine) {
        document.getElementById('routine').value = currentRoutine;
    }
    if (currentExercise) {
        document.getElementById('exercise').value = currentExercise;
        // Trigger change event for enhanced dropdown to update display
        document.getElementById('exercise').dispatchEvent(new Event('change', { bubbles: true }));
    }
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
            
            // Add event listener to validate input
            input.addEventListener('input', function() {
                const min = parseInt(this.min) || 0;
                const max = parseInt(this.max) || Infinity;
                let value = parseInt(this.value) || defaultValues[id];
                
                // Ensure value is within bounds
                value = Math.max(min, Math.min(max, value));
                this.value = value;
            });
        }
    });
}

export function initializeWorkoutPlanHandlers() {
    // Initialize default values
    initializeDefaultValues();

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
 * Handle view mode change (Simple/Advanced)
 * Updates displayed muscle values in the table without re-fetching data
 */
function handleViewModeChange(e) {
    const mode = e.detail?.mode;
    if (!mode) return;
    
    // Update muscle column displays using cached workout data
    updateMuscleDisplaysInTable();
}

/**
 * Update muscle display values in table based on current view mode
 * Uses data-raw-value attributes to re-transform values
 */
function updateMuscleDisplaysInTable() {
    const tbody = document.querySelector('#workout_plan_table_body');
    if (!tbody) return;
    
    // Update cells that have data-raw-value attribute
    tbody.querySelectorAll('[data-raw-value]').forEach(cell => {
        const rawValue = cell.getAttribute('data-raw-value');
        const isIsolated = cell.getAttribute('data-label') === 'Isolated Muscles';
        const row = cell.closest('tr');
        // Get isolated muscles from the same row for scientific mode
        const isolatedCell = row?.querySelector('[data-label="Isolated Muscles"]');
        const isolatedMuscles = isolatedCell?.getAttribute('data-raw-value') || null;
        cell.textContent = transformMuscleDisplay(rawValue, isIsolated ? 'isolated' : 'primary', isIsolated ? null : isolatedMuscles);
    });
}

/**
 * Initializes the routine tabs click handlers
 */
function initializeRoutineTabs() {
    const allTabBtn = document.querySelector('#routine-tabs [data-routine="all"]');
    if (allTabBtn) {
        allTabBtn.addEventListener('click', () => handleRoutineTabClick('all'));
    }
}

export function updateWorkoutPlanTable(exercises) {
    const tbody = document.querySelector('#workout_plan_table_body');
    if (!tbody) {
        console.error('Workout plan table body not found');
        return;
    }

    tbody.innerHTML = '';
    
    // Reset selection state when table is rebuilt
    selectedExerciseIds.clear();
    updateSupersetActionButtons();

    // Sort exercises: first by routine (Environment > Program > Workout), 
    // then by exercise_order within each routine
    exercises.sort((a, b) => {
        // First sort by routine (Environment - Program - Workout)
        const routineCompare = compareRoutines(a.routine, b.routine);
        if (routineCompare !== 0) {
            return routineCompare;
        }
        // Within the same routine, sort by exercise_order
        const orderA = a.exercise_order || 0;
        const orderB = b.exercise_order || 0;
        return orderA - orderB;
    });
    
    // Build superset color map and identify superset pairs
    supersetColorMap.clear();
    let colorIndex = 0;
    const supersetGroups = new Map(); // Maps superset_group to array of exercise indices
    
    exercises.forEach((ex, idx) => {
        if (ex.superset_group) {
            if (!supersetGroups.has(ex.superset_group)) {
                supersetGroups.set(ex.superset_group, []);
                colorIndex = (colorIndex % 4) + 1;
                supersetColorMap.set(ex.superset_group, colorIndex);
            }
            supersetGroups.get(ex.superset_group).push(idx);
        }
    });

    exercises.forEach((exercise, idx) => {
        const row = document.createElement('tr');
        row.dataset.exerciseId = exercise.id;
        row.dataset.routine = exercise.routine || '';
        
        // Determine superset styling
        let supersetClasses = '';
        let supersetBadgeHtml = '';
        const supersetGroup = exercise.superset_group;
        
        if (supersetGroup) {
            const groupIndices = supersetGroups.get(supersetGroup) || [];
            const posInGroup = groupIndices.indexOf(idx);
            const colorNum = supersetColorMap.get(supersetGroup) || 1;
            
            row.dataset.supersetGroup = supersetGroup;
            supersetClasses = `superset-group superset-group-${colorNum}`;
            
            // Only add superset-first/superset-last classes if exercises are actually adjacent
            // This prevents broken visual connectors when viewing "All" routines
            const isAdjacentSuperset = groupIndices.length >= 2 && 
                (groupIndices[1] - groupIndices[0] === 1);
            
            if (isAdjacentSuperset) {
                if (posInGroup === 0) {
                    supersetClasses += ' superset-first';
                } else if (posInGroup === groupIndices.length - 1) {
                    supersetClasses += ' superset-last';
                }
            }
            
            supersetBadgeHtml = `<span class="superset-badge" style="--superset-row-color: var(--superset-color-${colorNum})"><i class="fas fa-link"></i> SS</span>`;
        }
        
        if (supersetClasses) {
            row.className = supersetClasses;
        }
        
        // Add checkbox column, drag handle and other cells with priority classes and data-labels
        row.innerHTML = `
            <td class="superset-select-col" data-label="Select">
                <input type="checkbox" class="superset-checkbox" 
                       data-exercise-id="${exercise.id}" 
                       data-routine="${exercise.routine || ''}"
                       data-superset-group="${supersetGroup || ''}"
                       aria-label="Select ${exercise.exercise} for superset">
            </td>
            <td class="drag-handle" title="Drag to reorder">
                <i class="fas fa-grip-vertical"></i>
            </td>
            <td class="col--high routine-cell" data-label="Routine">${formatRoutineForDisplay(exercise.routine)}</td>
            <td class="col--high exercise-cell" data-label="Exercise">
                <span class="exercise-name">${exercise.exercise || 'N/A'}</span>
                ${supersetBadgeHtml}
                <button class="btn btn-swap btn-calm-icon"
                        data-exercise-id="${exercise.id}"
                        title="Replace with similar exercise (same muscle + equipment)"
                        aria-label="Swap exercise">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </td>
            <td class="col--med" data-label="Primary Muscle" data-raw-value="${exercise.primary_muscle_group || ''}">${transformMuscleDisplay(exercise.primary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Secondary Muscle" data-raw-value="${exercise.secondary_muscle_group || ''}">${transformMuscleDisplay(exercise.secondary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Tertiary Muscle" data-raw-value="${exercise.tertiary_muscle_group || ''}">${transformMuscleDisplay(exercise.tertiary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Isolated Muscles" data-raw-value="${exercise.advanced_isolated_muscles || ''}">${transformMuscleDisplay(exercise.advanced_isolated_muscles, 'isolated')}</td>
            <td class="col--low" data-label="Utility">${exercise.utility || 'N/A'}</td>
            <td class="col--low" data-label="Movement Pattern">${exercise.movement_pattern || 'N/A'}</td>
            <td class="col--low" data-label="Movement Subpattern">${exercise.movement_subpattern || 'N/A'}</td>
            <td class="col--high is-num editable" data-field="sets" data-label="Sets">${exercise.sets || 'N/A'}</td>
            <td class="col--high is-num editable" data-field="min_rep_range" data-label="Min Rep">${exercise.min_rep_range || 'N/A'}</td>
            <td class="col--high is-num editable" data-field="max_rep_range" data-label="Max Rep">${exercise.max_rep_range || 'N/A'}</td>
            <td class="col--med is-num editable" data-field="rir" data-label="RIR">${exercise.rir || 'N/A'}</td>
            <td class="col--med is-num editable" data-field="rpe" data-label="RPE">${exercise.rpe || 'N/A'}</td>
            <td class="col--high is-num editable" data-field="weight" data-label="Weight">${exercise.weight || 'N/A'}</td>
            <td class="col--med execution-style-cell" data-label="Execution Style" data-exercise-id="${exercise.id}">
                ${renderExecutionStyleBadge(exercise)}
            </td>
            <td class="col--low" data-label="Grips">${exercise.grips || 'N/A'}</td>
            <td class="col--low" data-label="Stabilizers">${exercise.stabilizers || 'N/A'}</td>
            <td class="col--low" data-label="Synergists">${exercise.synergists || 'N/A'}</td>
            <td class="col--high" data-label="Actions">
                <button class="btn btn-danger btn-sm text-white btn-calm-danger" onclick="removeExercise(${exercise.id})">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </td>
        `;

        // Add click handlers for editable cells
        row.querySelectorAll('.editable').forEach(cell => {
            cell.addEventListener('click', () => {
                makeTableCellEditable(cell, exercise.id, cell.dataset.field);
            });
        });
        
        // Add click handler for swap button
        const swapBtn = row.querySelector('.btn-swap');
        if (swapBtn) {
            swapBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleSwapExercise(exercise.id, exercise.exercise);
            });
        }
        
        // Add click handler for superset checkbox
        const checkbox = row.querySelector('.superset-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                handleSupersetCheckboxChange(e.target);
            });
        }
        
        // Add click handler for execution style badge
        const execStyleCell = row.querySelector('.execution-style-cell');
        if (execStyleCell) {
            execStyleCell.addEventListener('click', (e) => {
                e.stopPropagation();
                showExecutionStylePicker(exercise.id, exercise);
            });
        }
        
        tbody.appendChild(row);
    });

    // Initialize drag and drop after populating the table
    initializeDragAndDrop();
    
    // Initialize superset action buttons
    initializeSupersetActions();
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
        selectedExerciseIds.add(exerciseId);
        row.classList.add('superset-selected');
    } else {
        selectedExerciseIds.delete(exerciseId);
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
    
    const selectedCount = selectedExerciseIds.size;
    
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
    if (selectedExerciseIds.size !== 2) {
        showToast('Please select exactly 2 exercises to create a superset', true);
        return;
    }
    
    const exerciseIds = Array.from(selectedExerciseIds);
    
    try {
        const data = await api.post('/api/superset/link', { exercise_ids: exerciseIds }, { showErrorToast: false });
        
        showToast(data.message || 'Superset created successfully');
        // Clear selection and refresh table
        selectedExerciseIds.clear();
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
        const data = await api.post('/api/superset/unlink', { exercise_id: exerciseId }, { showErrorToast: false });
        
        showToast(data.message || 'Superset unlinked successfully');
        // Clear selection and refresh table
        selectedExerciseIds.clear();
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
    swapBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    swapBtn.classList.add('loading');
    
    try {
        const data = await api.post('/replace_exercise', {
            id: exerciseId,
            strategy: 'ai'  // Try AI-based suggestion first
        }, { showLoading: false, showErrorToast: false }); // We handle our own loading state
        
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
            
            // Brief highlight effect on the row
            row.classList.add('row-swapped');
            setTimeout(() => row.classList.remove('row-swapped'), 2000);
            
        } else {
            // Handle specific error reasons
            const reason = responseData?.error?.reason || 'unknown';
            const message = responseData?.error?.message || responseData?.message || 'Failed to replace exercise';
            
            if (reason === 'no_candidates') {
                showToast('warning', 'No alternative found for this muscle/equipment.');
            } else if (reason === 'duplicate') {
                showToast('warning', 'All alternatives are already in this routine.');
            } else if (reason === 'not_found') {
                showToast('error', 'Exercise not found in workout plan.');
            } else if (reason === 'missing_metadata') {
                showToast('warning', 'This exercise is missing muscle/equipment data and cannot be replaced.');
            } else {
                showToast('error', message);
            }
        }
        
    } catch (error) {
        console.error('Error swapping exercise:', error);
        // Handle specific error reasons from the error object
        const reason = error?.reason || 'unknown';
        const message = error?.message || 'Failed to replace exercise. Please try again.';
        
        if (reason === 'no_candidates') {
            showToast('warning', 'No alternative found for this muscle/equipment.');
        } else if (reason === 'duplicate') {
            showToast('warning', 'All alternatives are already in this routine.');
        } else if (reason === 'not_found') {
            showToast('error', 'Exercise not found in workout plan.');
        } else if (reason === 'missing_metadata') {
            showToast('warning', 'This exercise is missing muscle/equipment data and cannot be replaced.');
        } else {
            showToast('error', message);
        }
    } finally {
        // Restore button state
        swapBtn.disabled = false;
        swapBtn.innerHTML = originalIcon;
        swapBtn.classList.remove('loading');
    }
}

/**
 * Updates the metadata cells in a row after a swap
 * @param {HTMLElement} row - The table row element
 * @param {Object} updatedData - The updated exercise data
 */
function updateRowMetadata(row, updatedData) {
    // Map of data-label to data key
    const labelToKey = {
        'Primary Muscle': 'primary_muscle_group',
        'Secondary Muscle': 'secondary_muscle_group',
        'Tertiary Muscle': 'tertiary_muscle_group',
        'Isolated Muscles': 'advanced_isolated_muscles',
        'Utility': 'utility',
        'Grips': 'grips',
        'Stabilizers': 'stabilizers',
        'Synergists': 'synergists'
    };
    
    // Update each cell that has a data-label matching our map
    Object.entries(labelToKey).forEach(([label, key]) => {
        const cell = row.querySelector(`td[data-label="${label}"]`);
        if (cell) {
            cell.textContent = updatedData[key] || 'N/A';
        }
    });
}

/**
 * Updates the cached exercise data after a swap
 * @param {number} exerciseId - The exercise ID that was updated
 * @param {Object} updatedData - The new exercise data
 */
function updateCachedExercise(exerciseId, updatedData) {
    // Update allExercisesCache if it exists
    const cacheIndex = allExercisesCache.findIndex(ex => ex.id === exerciseId);
    if (cacheIndex !== -1) {
        // Merge the updated data while preserving exercise_order
        allExercisesCache[cacheIndex] = {
            ...allExercisesCache[cacheIndex],
            ...updatedData
        };
    }
}


function makeTableCellEditable(cell, exerciseId, fieldName) {
    // Prevent creating multiple inputs if already editing
    if (cell.querySelector('input')) {
        return;
    }
    
    const originalValue = cell.textContent.trim();
    const input = document.createElement('input');
    input.type = 'number';
    input.value = originalValue === 'N/A' ? '' : originalValue;
    input.className = 'form-control form-control-sm input-calm-inset';
    input.dataset.originalValue = originalValue;
    
    // Add validation rules based on field type
    switch(fieldName) {
        case 'sets':
            input.min = 1;
            input.max = 10;
            break;
        case 'min_rep_range':
        case 'max_rep_range':
            input.min = 1;
            input.max = 30;
            break;
        case 'rir':
            input.min = 0;
            input.max = 10;
            break;
        case 'rpe':
            input.min = 1;
            input.max = 10;
            input.step = 0.5;
            break;
        case 'weight':
            input.min = 0;
            input.step = 0.5;
            break;
    }

    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    const finishEditing = async (save = true) => {
        const storedOriginal = input.dataset.originalValue;
        const newValue = input.value.trim();
        
        // Remove input and restore cell
        if (input.parentNode === cell) {
            cell.removeChild(input);
        }
        
        if (save && newValue && newValue !== storedOriginal) {
            try {
                const response = await updateExerciseField(exerciseId, fieldName, newValue);
                if (response.ok) {
                    cell.textContent = newValue;
                    showToast('Exercise updated successfully');
                } else {
                    throw new Error('Update failed');
                }
            } catch (error) {
                console.error('Error updating exercise:', error);
                cell.textContent = storedOriginal;
                showToast('Failed to update exercise', true);
            }
        } else {
            cell.textContent = newValue || storedOriginal;
        }
    };

    // Use mousedown to detect clicks outside the input
    const handleClickOutside = (e) => {
        if (!cell.contains(e.target)) {
            document.removeEventListener('mousedown', handleClickOutside);
            finishEditing(true);
        }
    };
    
    // Delay adding the outside click handler to prevent immediate trigger
    setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
    }, 10);

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.removeEventListener('mousedown', handleClickOutside);
            finishEditing(true);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            document.removeEventListener('mousedown', handleClickOutside);
            finishEditing(false);
        }
    });
}

async function updateExerciseField(exerciseId, fieldName, value) {
    const updates = { [fieldName]: value };
    // Use api wrapper with showLoading: false for quick inline edits
    const data = await api.post('/update_exercise', {
        id: exerciseId,
        updates: updates
    }, { showLoading: false, showErrorToast: false });
    
    return data.data || data;
}

// Add this function to initialize drag-and-drop
function initializeDragAndDrop() {
    const tbody = document.querySelector('#workout_plan_table_body');
    if (!tbody) return;

    Sortable.create(tbody, {
        animation: 150,
        handle: '.drag-handle',
        onStart: function(evt) {
            // If dragging a superset item, mark its partner for visual feedback
            const draggedRow = evt.item;
            const supersetGroup = draggedRow.dataset.supersetGroup;
            if (supersetGroup) {
                const partnerRow = tbody.querySelector(`tr[data-superset-group="${supersetGroup}"]:not([data-exercise-id="${draggedRow.dataset.exerciseId}"])`);
                if (partnerRow) {
                    partnerRow.classList.add('superset-partner-dragging');
                }
            }
        },
        onEnd: async function(evt) {
            // Remove partner dragging class
            tbody.querySelectorAll('.superset-partner-dragging').forEach(row => {
                row.classList.remove('superset-partner-dragging');
            });
            
            const draggedRow = evt.item;
            const supersetGroup = draggedRow.dataset.supersetGroup;
            
            // If the dragged row is part of a superset, move its partner to be adjacent
            if (supersetGroup) {
                const allRows = Array.from(tbody.querySelectorAll('tr'));
                const draggedIndex = allRows.indexOf(draggedRow);
                const partnerRow = tbody.querySelector(`tr[data-superset-group="${supersetGroup}"]:not([data-exercise-id="${draggedRow.dataset.exerciseId}"])`);
                
                if (partnerRow) {
                    const partnerIndex = allRows.indexOf(partnerRow);
                    
                    // Check if partner is not already adjacent
                    if (Math.abs(draggedIndex - partnerIndex) !== 1) {
                        // Move partner to be right after the dragged row
                        if (draggedRow.nextSibling !== partnerRow) {
                            draggedRow.parentNode.insertBefore(partnerRow, draggedRow.nextSibling);
                        }
                    }
                }
            }
            
            // Now get the final order and save it
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const orderData = rows.map((row, index) => ({
                id: parseInt(row.dataset.exerciseId),
                order: index + 1
            }));

            try {
                const data = await api.post('/update_exercise_order', orderData, { showLoading: false, showErrorToast: false });

                showToast(data.message || 'Exercise order updated successfully');
                
                // Refresh table to update superset visual styling
                // Small delay to ensure database transaction is complete
                await new Promise(resolve => setTimeout(resolve, 50));
                await fetchWorkoutPlan();
            } catch (error) {
                console.error('Error updating exercise order:', error);
                showToast(error.message || 'Failed to update exercise order', true);
                // Refresh the table to restore original order
                await fetchWorkoutPlan();
            }
        }
    });
}
