import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';
import { buildPlayButton } from './exercise-video-modal.js';
import { escapeHtml, resolveExerciseMediaSrc } from './exercise-helpers.js';
import { initializeExerciseImagePreview } from './exercise-image-preview.js';
import { workoutPlanState } from './workout-plan-state.js';
import {
    applyRoutineTabFilter,
    buildAddExercisePayload,
    buildExecutionStylePayload,
    buildExerciseOrderPayload,
    buildFieldUpdatePayload,
    buildReplacePayload,
    buildSupersetLinkPayload,
    buildSupersetUnlinkPayload,
    clampToAttrRange,
    collectMissingAddFields,
    collectMissingRequiredSelections,
    compareRoutines,
    computeNudgedValue,
    estimateProvenanceLabel,
    fatigueChipTitle,
    formatRoutineForDisplay,
    formatRoutineForTab,
    learnedBadgeText,
    nextSupersetColorIndex,
    renderExecutionStyleBadge,
    resolveMin,
    resolveProfileEstimate,
    resolveStep,
    resolveSwapErrorToast,
    supersetRowClasses,
    traceHeadline,
    traceStepValueText,
} from './workout-plan-helpers.js';

initializeExerciseImagePreview();

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

function getSwapButtonMarkup() {
    return `
        <span class="btn-swap-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16" focusable="false">
                <path d="M10.75 3.25h2.7L11.8 1.6a.75.75 0 1 1 1.06-1.06l2.93 2.93a.75.75 0 0 1 0 1.06l-2.93 2.93A.75.75 0 1 1 11.8 6.4l1.65-1.65h-2.7a3.25 3.25 0 0 0-2.82 1.63.75.75 0 1 1-1.3-.75 4.75 4.75 0 0 1 4.12-2.38Zm-5.5 8.5h-2.7L4.2 13.4a.75.75 0 1 1-1.06 1.06L.21 11.53a.75.75 0 0 1 0-1.06l2.93-2.93A.75.75 0 1 1 4.2 8.6L2.55 10.25h2.7a3.25 3.25 0 0 0 2.82-1.63.75.75 0 1 1 1.3.75 4.75 4.75 0 0 1-4.12 2.38Z" fill="currentColor"/>
            </svg>
        </span>
        <span class="btn-swap-label">Swap</span>
    `;
}

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
        if (routine === workoutPlanState.currentRoutineTabFilter) {
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
    if (workoutPlanState.currentRoutineTabFilter === 'all') {
        const allTabBtn = tabsContainer.querySelector('[data-routine="all"]');
        if (allTabBtn) {
            allTabBtn.classList.add('active');
            allTabBtn.setAttribute('aria-selected', 'true');
        }
    }
    
    // If the current filter's routine no longer exists, reset to "all"
    if (workoutPlanState.currentRoutineTabFilter !== 'all' && !sortedRoutines.includes(workoutPlanState.currentRoutineTabFilter)) {
        workoutPlanState.currentRoutineTabFilter = 'all';
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
    workoutPlanState.currentRoutineTabFilter = routine;
    
    // Apply filter and re-render table
    const filteredExercises = applyRoutineTabFilter(workoutPlanState.allExercisesCache, routine);
    updateWorkoutPlanTable(filteredExercises);
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

function setWorkoutControlValue(id, value) {
    const field = document.getElementById(id);
    if (!field || value === undefined || value === null) {
        return;
    }
    field.value = String(value);
}

// Tracks whether the user has manually edited the Weight input since the last
// exercise selection. While true, the profile estimate must not overwrite the
// user's value (Issue #5).
let weightUserDirty = false;

function resetWeightDirtyForTests() {
    weightUserDirty = false;
}

function markWeightUserDirty() {
    weightUserDirty = true;
}

function initializeWeightDirtyTracking() {
    const weightInput = document.getElementById('weight');
    if (!weightInput || weightInput.dataset.dirtyTracked === 'true') return;
    weightInput.addEventListener('input', markWeightUserDirty);
    weightInput.dataset.dirtyTracked = 'true';
}

function applyEstimateToWorkoutControls(estimate) {
    const resolved = resolveProfileEstimate(estimate);
    if (!weightUserDirty) {
        setWorkoutControlValue('weight', resolved.weight);
    }
    setWorkoutControlValue('sets', resolved.sets);
    setWorkoutControlValue('min_rep', resolved.min_rep);
    setWorkoutControlValue('max_rep_range', resolved.max_rep);
    setWorkoutControlValue('rir', resolved.rir);
    setWorkoutControlValue('rpe', resolved.rpe);

    const provenance = document.getElementById('workout-estimate-provenance');
    if (provenance) {
        provenance.textContent = estimateProvenanceLabel(resolved.source);
    }

    updateLearnedBadge(resolved);
    updateFatigueContextChip(resolved);

    const handHint = document.getElementById('weight-hand-hint');
    if (handHint) {
        handHint.hidden = !resolved.is_dumbbell;
    }

    updateEstimateTraceUI(resolved);
}

// Learned Calibration — compact source badge next to the provenance line.
// Shown only when the estimator returned a learned suggestion (settings mode
// `suggest` + usable confidence). The confidence drives the badge tint.
function updateLearnedBadge(estimate) {
    const badge = document.getElementById('workout-estimate-learned-badge');
    if (!badge) return;
    const info = learnedBadgeText(estimate);
    if (!info.isLearned) {
        badge.hidden = true;
        badge.dataset.confidence = '';
        badge.removeAttribute('title');
        return;
    }
    badge.hidden = false;
    badge.dataset.confidence = info.confidence;
    const label = badge.querySelector('.workout-estimate-learned-badge-label');
    if (label) {
        label.textContent = info.label;
    }
    badge.title = info.title;
}

// Fatigue context (Phase 2D-A) — neutral, non-source chip next to the
// provenance line. Shown only when the estimate carries the additive
// `fatigue_context` advisory block (its own default-off Profile toggle). It is
// deliberately NOT confidence-tinted and NEVER implies the number changed.
function updateFatigueContextChip(estimate) {
    const chip = document.getElementById('workout-estimate-fatigue-chip');
    if (!chip) return;
    const fatigue = estimate?.fatigue_context;
    if (!fatigue) {
        chip.hidden = true;
        chip.removeAttribute('title');
        return;
    }
    chip.hidden = false;
    chip.title = fatigueChipTitle(fatigue);
}

// Force the current learned suggestion into the Workout Controls inputs.
// Client-side only — populates inputs, never persists to user_selection
// (plan §"User Actions": Apply suggestion is client-side for the MVP).
function applyLearnedSuggestionToInputs() {
    const estimate = latestTracePayload;
    if (!estimate) return;
    setWorkoutControlValue('weight', estimate.weight);
    setWorkoutControlValue('sets', estimate.sets);
    setWorkoutControlValue('min_rep', estimate.min_rep);
    setWorkoutControlValue('max_rep_range', estimate.max_rep);
    setWorkoutControlValue('rir', estimate.rir);
    setWorkoutControlValue('rpe', estimate.rpe);
    // The user explicitly accepted the suggestion, so the weight is no longer a
    // pending manual edit — let later estimates flow in again.
    resetWeightDirtyForTests();
    showToast('Suggestion applied');
}

async function resetLearnedForCurrentExercise() {
    const exerciseName = document.getElementById('exercise')?.value || '';
    if (!exerciseName) return;
    try {
        await api.post('/api/user_profile/calibration/reset', { exercise: exerciseName });
        showToast('success', 'Learned data reset for this exercise');
        // Re-fetch so the controls fall back to the last-log / Profile estimate.
        await applyUserProfileEstimateForSelectedExercise();
    } catch (error) {
        showToast('error', error?.message || 'Failed to reset learned data', {
            requestId: error?.requestId,
        });
    }
}

async function ignoreRelatedTransferForCurrentExercise() {
    const estimate = latestTracePayload;
    const sourceExercise = estimate?.trace?.source_exercise || '';
    const targetExercise = estimate?.trace?.target_exercise
        || document.getElementById('exercise')?.value
        || '';
    if (!sourceExercise || !targetExercise) return;
    try {
        await api.post('/api/user_profile/calibration/ignore_transfer', {
            source_exercise: sourceExercise,
            target_exercise: targetExercise,
        });
        showToast('success', 'Related suggestion ignored for this exercise');
        await applyUserProfileEstimateForSelectedExercise();
    } catch (error) {
        showToast('error', error?.message || 'Failed to ignore related suggestion', {
            requestId: error?.requestId,
        });
    }
}

// Issue #17 — Plan-page "show the math" trace expander.
// The estimator (utils/profile_estimator.py) is the single source of truth
// for the trace shape. This module just renders it on click — it never
// reconstructs the math.
let latestTracePayload = null;

function updateEstimateTraceUI(estimate) {
    latestTracePayload = estimate || null;
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;

    const trace = estimate?.trace;
    const hasTrace = Boolean(trace && Array.isArray(trace.steps) && trace.steps.length > 0);
    if (!hasTrace) {
        toggle.hidden = true;
        container.hidden = true;
        container.innerHTML = '';
        toggle.setAttribute('aria-expanded', 'false');
        return;
    }
    toggle.hidden = false;
    // Collapse on each new estimate so the user opts back in for the new exercise.
    toggle.setAttribute('aria-expanded', 'false');
    container.hidden = true;
    container.innerHTML = '';
}

function renderEstimateTrace(estimate) {
    const container = document.getElementById('workout-estimate-trace');
    if (!container) return;
    container.innerHTML = '';
    const trace = estimate?.trace;
    if (!trace) return;

    const headline = document.createElement('p');
    headline.className = 'workout-estimate-trace-headline';
    headline.textContent = traceHeadline(trace.source);
    container.appendChild(headline);

    const list = document.createElement('ul');
    list.className = 'workout-estimate-trace-steps';
    for (const step of trace.steps) {
        const li = document.createElement('li');
        const labelEl = document.createElement('span');
        labelEl.className = 'workout-estimate-trace-step-label';
        labelEl.textContent = step.label;
        li.appendChild(labelEl);

        const valueText = traceStepValueText(step);
        if (valueText) {
            const valueEl = document.createElement('span');
            valueEl.className = 'workout-estimate-trace-step-value';
            valueEl.textContent = valueText;
            li.appendChild(valueEl);
        }

        if (step.detail) {
            const detailEl = document.createElement('small');
            detailEl.className = 'workout-estimate-trace-step-detail';
            detailEl.textContent = step.detail;
            li.appendChild(detailEl);
        }

        list.appendChild(li);
    }
    container.appendChild(list);

    // Phase 2D-A — advisory fatigue context, rendered as its own distinct
    // section BELOW the strength evidence. Never merged into the strength
    // steps; always carries the "does not change your suggestion" line.
    const fatigueSection = buildFatigueContextSection(estimate?.fatigue_context);
    if (fatigueSection) container.appendChild(fatigueSection);

    if (trace.improvement_hint?.copy) {
        const hint = document.createElement('p');
        hint.className = 'workout-estimate-trace-hint';
        const slug = trace.improvement_hint.lift_key;
        const link = document.createElement('a');
        link.href = slug
            ? `/user_profile#lift-${slug}-weight`
            : '/user_profile';
        link.textContent = 'Open Profile →';
        link.setAttribute('data-trace-improvement-link', '');
        hint.appendChild(document.createTextNode(trace.improvement_hint.copy + ' '));
        hint.appendChild(link);
        container.appendChild(hint);
    }

    if (['learned', 'related_learned'].includes(trace.source)) {
        container.appendChild(buildLearnedActions());
    }
}

// Build the advisory "Fatigue context" block for the trace details. Returns
// null when the estimate carries no fatigue_context (toggle off / no muscle).
// Read-only: an eyebrow, a headline, and the mandatory advisory line.
function buildFatigueContextSection(fatigue) {
    if (!fatigue) return null;
    const section = document.createElement('div');
    section.className = 'workout-estimate-fatigue';
    section.setAttribute('data-fatigue-context', '');

    const eyebrow = document.createElement('p');
    eyebrow.className = 'workout-estimate-fatigue-eyebrow';
    eyebrow.textContent = 'Fatigue context';
    section.appendChild(eyebrow);

    if (fatigue.headline) {
        const headline = document.createElement('p');
        headline.className = 'workout-estimate-fatigue-headline';
        headline.textContent = fatigue.headline;
        section.appendChild(headline);
    }

    const advisory = document.createElement('small');
    advisory.className = 'workout-estimate-fatigue-advisory';
    advisory.textContent = fatigue.advisory || 'This does not change your suggestion.';
    section.appendChild(advisory);

    // Phase 2D-C — optional manual-adjustment affordance. Neutral ± steppers for
    // Weight and Sets plus "Reset to suggestion". Client-side only: it edits the
    // Workout Controls inputs and never persists or calls an API (mirrors the MVP
    // `Apply suggestion` contract). It deliberately uses the inputs' own manual
    // step — NOT a fatigue-derived magnitude (that mapping is gated to 2D-D).
    section.appendChild(buildFatigueNudgeControls());

    return section;
}

// Resolve the manual step / floor of a Workout Controls number input from its
// own attributes. `step="any"` (weight) and an absent step (sets) both fall back
// to 1 — i.e. the input's native arrow-key step. No fatigue math here.
function resolveControlStep(input) {
    return resolveStep(input.getAttribute('step'));
}

function resolveControlMin(input) {
    return resolveMin(input.getAttribute('min'));
}

// Step a Workout Controls input up/down by its own manual step, clamped to the
// input's `min`. Client-side only — sets the value directly (no input event, so
// it never marks the weight "user-dirty" or triggers a re-estimate).
function nudgeWorkoutControl(id, direction) {
    const field = document.getElementById(id);
    if (!field) return;
    const step = resolveControlStep(field);
    const min = resolveControlMin(field);
    const current = parseFloat(field.value);
    const next = computeNudgedValue(current, step, min, direction);
    setWorkoutControlValue(id, next);
}

// Restore the estimator's original Weight + Sets exactly from the last estimate.
// `latestTracePayload` is the resolved estimate that was applied to the inputs,
// so this re-applies the suggestion the user is choosing to step away from.
function resetWorkoutControlsToSuggestion() {
    const estimate = latestTracePayload;
    if (!estimate) return;
    setWorkoutControlValue('weight', estimate.weight);
    setWorkoutControlValue('sets', estimate.sets);
}

// Build one labeled ± stepper group for a single Workout Controls input.
function buildFatigueNudgeGroup(id, label) {
    const group = document.createElement('div');
    group.className = 'workout-estimate-fatigue-nudge-group';

    const name = document.createElement('span');
    name.className = 'workout-estimate-fatigue-nudge-name';
    name.textContent = label;
    group.appendChild(name);

    for (const direction of ['down', 'up']) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'workout-estimate-fatigue-nudge-btn';
        btn.setAttribute('data-nudge', id);
        btn.setAttribute('data-nudge-dir', direction);
        btn.setAttribute(
            'aria-label',
            `${direction === 'down' ? 'Decrease' : 'Increase'} ${label.toLowerCase()}`,
        );
        btn.textContent = direction === 'down' ? '−' : '+';
        btn.addEventListener('click', () => nudgeWorkoutControl(id, direction));
        group.appendChild(btn);
    }
    return group;
}

// Build the manual nudge block appended to the fatigue context section. Only
// renders a stepper for a control that actually exists in Workout Controls
// (weight + sets per Phase 2D-C scope; reps deferred to a later slice).
function buildFatigueNudgeControls() {
    const wrap = document.createElement('div');
    wrap.className = 'workout-estimate-fatigue-nudge';
    wrap.setAttribute('data-fatigue-nudge', '');

    const label = document.createElement('p');
    label.className = 'workout-estimate-fatigue-nudge-label';
    label.textContent = 'Adjust manually';
    wrap.appendChild(label);

    const row = document.createElement('div');
    row.className = 'workout-estimate-fatigue-nudge-row';
    for (const spec of [{ id: 'weight', label: 'Weight' }, { id: 'sets', label: 'Sets' }]) {
        if (!document.getElementById(spec.id)) continue;
        row.appendChild(buildFatigueNudgeGroup(spec.id, spec.label));
    }
    wrap.appendChild(row);

    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'workout-estimate-trace-action is-reset';
    reset.setAttribute('data-fatigue-nudge-reset', '');
    reset.textContent = 'Reset to suggestion';
    reset.addEventListener('click', resetWorkoutControlsToSuggestion);
    wrap.appendChild(reset);

    return wrap;
}

// Apply / Keep / Reset row shown inside the learned-suggestion details. Apply
// is client-side only; Reset clears the stored row and re-fetches the estimate.
function buildLearnedActions() {
    const actions = document.createElement('div');
    actions.className = 'workout-estimate-trace-actions';

    const apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'workout-estimate-trace-action is-primary';
    apply.setAttribute('data-learned-apply', '');
    apply.textContent = 'Apply suggestion';
    apply.addEventListener('click', applyLearnedSuggestionToInputs);

    const keep = document.createElement('button');
    keep.type = 'button';
    keep.className = 'workout-estimate-trace-action';
    keep.setAttribute('data-learned-keep', '');
    keep.textContent = 'Keep current';
    keep.addEventListener('click', collapseEstimateTrace);

    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'workout-estimate-trace-action is-reset';
    reset.setAttribute('data-learned-reset', '');
    reset.textContent = 'Reset learned data';
    reset.addEventListener('click', resetLearnedForCurrentExercise);

    actions.append(apply, keep, reset);
    if (latestTracePayload?.source === 'related_learned') {
        const ignore = document.createElement('button');
        ignore.type = 'button';
        ignore.className = 'workout-estimate-trace-action is-reset';
        ignore.setAttribute('data-related-ignore', '');
        ignore.textContent = 'Ignore this source';
        ignore.addEventListener('click', ignoreRelatedTransferForCurrentExercise);
        actions.append(ignore);
    }
    return actions;
}

function collapseEstimateTrace() {
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;
    toggle.setAttribute('aria-expanded', 'false');
    container.hidden = true;
    const labelEl = toggle.querySelector('.workout-estimate-trace-toggle-label');
    if (labelEl) labelEl.textContent = 'Show the math';
}

function bindEstimateTraceToggle() {
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;
    toggle.addEventListener('click', () => {
        const expanded = toggle.getAttribute('aria-expanded') === 'true';
        const next = !expanded;
        toggle.setAttribute('aria-expanded', String(next));
        container.hidden = !next;
        if (next && latestTracePayload && container.children.length === 0) {
            renderEstimateTrace(latestTracePayload);
        }
        const labelEl = toggle.querySelector('.workout-estimate-trace-toggle-label');
        if (labelEl) {
            labelEl.textContent = next ? 'Hide the math' : 'Show the math';
        }
    });
}

export async function applyUserProfileEstimateForSelectedExercise() {
    const exerciseName = document.getElementById('exercise')?.value || '';

    try {
        const response = await api.get(
            `/api/user_profile/estimate?exercise=${encodeURIComponent(exerciseName)}`,
            { showLoading: false, showErrorToast: false, retries: 0 }
        );
        applyEstimateToWorkoutControls(response.data || response);
    } catch (error) {
        console.warn('Unable to apply user profile estimate:', error);
        applyEstimateToWorkoutControls(null);
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
        weightUserDirty = false;
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
    weightUserDirty = false;
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
    workoutPlanState.selectedExerciseIds.clear();
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
    workoutPlanState.supersetColorMap.clear();
    let colorIndex = 0;
    const supersetGroups = new Map(); // Maps superset_group to array of exercise indices
    
    exercises.forEach((ex, idx) => {
        if (ex.superset_group) {
            if (!supersetGroups.has(ex.superset_group)) {
                supersetGroups.set(ex.superset_group, []);
                colorIndex = nextSupersetColorIndex(colorIndex);
                workoutPlanState.supersetColorMap.set(ex.superset_group, colorIndex);
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
            const colorNum = workoutPlanState.supersetColorMap.get(supersetGroup) || 1;
            
            row.dataset.supersetGroup = supersetGroup;
            supersetClasses = supersetRowClasses(colorNum, posInGroup, groupIndices);
            
            supersetBadgeHtml = `<span class="superset-badge" style="--superset-row-color: var(--superset-color-${colorNum})"><i class="fas fa-link"></i> SS</span>`;
        }
        
        if (supersetClasses) {
            row.className = supersetClasses;
        }
        
        const exerciseName = exercise.exercise || 'N/A';
        const mediaSrc = resolveExerciseMediaSrc(exercise.media_path);
        const thumbnailHtml = mediaSrc
            ? `<img class="exercise-thumbnail" src="${escapeHtml(mediaSrc)}" alt="${escapeHtml(exerciseName)} reference" data-preview-label="${escapeHtml(exerciseName)}" loading="lazy" width="32" height="32" tabindex="0">`
            : '';

        // Add checkbox column, drag handle and other cells with priority classes and data-labels
        row.innerHTML = `
            <td class="superset-select-col" data-label="Select">
                <input type="checkbox" class="superset-checkbox"
                       data-exercise-id="${exercise.id}"
                       data-routine="${escapeHtml(exercise.routine || '')}"
                       data-superset-group="${escapeHtml(supersetGroup || '')}"
                       aria-label="Select ${escapeHtml(exerciseName)} for superset">
            </td>
            <td class="drag-handle" title="Drag to reorder">
                <i class="fas fa-grip-vertical"></i>
            </td>
            <td class="col--high routine-cell" data-label="Routine">${formatRoutineForDisplay(exercise.routine)}</td>
            <td class="col--high exercise-cell" data-label="Exercise">
                <div class="exercise-cell-content">
                    ${thumbnailHtml}
                    <span class="exercise-name">${escapeHtml(exerciseName)}</span>
                    ${supersetBadgeHtml}
                    <button type="button"
                            class="btn btn-swap btn-calm-ghost"
                            data-action="replace"
                            data-exercise-id="${exercise.id}"
                            title="Replace with similar exercise (same muscle + equipment)"
                            aria-label="Swap exercise">
                        ${getSwapButtonMarkup()}
                    </button>
                </div>
            </td>
            <td class="col--med" data-label="Primary Muscle" data-raw-value="${escapeHtml(exercise.primary_muscle_group || '')}">${transformMuscleDisplay(exercise.primary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Secondary Muscle" data-raw-value="${escapeHtml(exercise.secondary_muscle_group || '')}">${transformMuscleDisplay(exercise.secondary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Tertiary Muscle" data-raw-value="${escapeHtml(exercise.tertiary_muscle_group || '')}">${transformMuscleDisplay(exercise.tertiary_muscle_group, 'primary', exercise.advanced_isolated_muscles)}</td>
            <td class="col--low" data-label="Isolated Muscles" data-raw-value="${escapeHtml(exercise.advanced_isolated_muscles || '')}">${transformMuscleDisplay(exercise.advanced_isolated_muscles, 'isolated')}</td>
            <td class="col--low" data-label="Utility">${escapeHtml(exercise.utility || 'N/A')}</td>
            <td class="col--low" data-label="Movement Pattern">${escapeHtml(exercise.movement_pattern || 'N/A')}</td>
            <td class="col--low" data-label="Movement Subpattern">${escapeHtml(exercise.movement_subpattern || 'N/A')}</td>
            <td class="col--high is-num editable" data-field="sets" data-label="Sets">${escapeHtml(exercise.sets ?? 'N/A')}</td>
            <td class="col--high is-num editable" data-field="min_rep_range" data-label="Min Rep">${escapeHtml(exercise.min_rep_range ?? 'N/A')}</td>
            <td class="col--high is-num editable" data-field="max_rep_range" data-label="Max Rep">${escapeHtml(exercise.max_rep_range ?? 'N/A')}</td>
            <td class="col--med is-num editable" data-field="rir" data-label="RIR">${escapeHtml(exercise.rir ?? 'N/A')}</td>
            <td class="col--med is-num editable" data-field="rpe" data-label="RPE">${escapeHtml(exercise.rpe ?? 'N/A')}</td>
            <td class="col--high is-num editable" data-field="weight" data-label="Weight">${escapeHtml(exercise.weight ?? 'N/A')}</td>
            <td class="col--med execution-style-cell" data-label="Execution Style" data-exercise-id="${exercise.id}">
                ${renderExecutionStyleBadge(exercise)}
            </td>
            <td class="col--low" data-label="Grips">${escapeHtml(exercise.grips || 'N/A')}</td>
            <td class="col--low" data-label="Stabilizers">${escapeHtml(exercise.stabilizers || 'N/A')}</td>
            <td class="col--low" data-label="Synergists">${escapeHtml(exercise.synergists || 'N/A')}</td>
            <td class="col--high" data-label="Actions">
                <button class="btn btn-danger btn-sm text-white btn-calm-danger" onclick="removeExercise(${exercise.id})">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </td>
        `;

        // §5 — append the reference-video play button into the Exercise cell
        // action cluster (next to Swap). DOM-node creation avoids interpolating
        // exercise-name into an inline aria-label or onclick.
        const cellContent = row.querySelector('.exercise-cell-content');
        if (cellContent) {
            const playBtn = buildPlayButton({
                videoId: exercise.youtube_video_id,
                exerciseName: exercise.exercise || '',
            });
            cellContent.appendChild(playBtn);
        }

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
    const cacheIndex = workoutPlanState.allExercisesCache.findIndex(ex => ex.id === exerciseId);
    if (cacheIndex !== -1) {
        // Merge the updated data while preserving exercise_order
        workoutPlanState.allExercisesCache[cacheIndex] = {
            ...workoutPlanState.allExercisesCache[cacheIndex],
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
                    if (fieldName === 'sets') {
                        notifyVolumeAffectingPlanChange('sets-edit');
                    }
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
    // Use api wrapper with showLoading: false for quick inline edits
    const data = await api.post('/update_exercise', buildFieldUpdatePayload(exerciseId, fieldName, value), { showLoading: false, showErrorToast: false });
    
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
            const orderData = buildExerciseOrderPayload(rows.map(row => parseInt(row.dataset.exerciseId)));

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
