// Workout plan table module (Refactor Plan v3 WP3.4b).
//
// Mechanical feature-split extracted from workout-plan.js: the plan table
// renderer, routine tabs, muscle-column display transforms, inline cell
// editing, per-row cache/metadata operations, and drag-and-drop reordering.
// Behavior is preserved exactly — this is a move-only change.
//
// The table renderer and drag behavior call into features that stay in
// workout-plan.js for later slices (swap → WP3.4e, supersets → WP3.4g,
// execution style → WP3.4d, plan refresh → the orchestration boundary). Rather
// than import those back — which would create a circular import — workout-plan.js
// injects them once at load via configureWorkoutPlanTable(). The shared mutable
// state singleton (workout-plan-state.js, WP3.3) is imported directly.
import { workoutPlanState } from './workout-plan-state.js';
import {
    applyRoutineTabFilter,
    buildExerciseOrderPayload,
    buildFieldUpdatePayload,
    compareRoutines,
    formatRoutineForDisplay,
    formatRoutineForTab,
    nextSupersetColorIndex,
    renderExecutionStyleBadge,
    supersetRowClasses,
} from './workout-plan-helpers.js';
import { escapeHtml } from './exercise-helpers.js';
import {
    appendExerciseVideoButton,
    buildExerciseThumbnailHtml,
} from './workout-plan-media.js';
import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';

// Feature callbacks injected by workout-plan.js so the table module never
// imports back into the monolith (no circular import). Defaults are no-ops so a
// bare updateWorkoutPlanTable() call before configuration cannot throw; in every
// real path workout-plan.js runs configureWorkoutPlanTable() at import time.
const tableDeps = {
    onSwap: () => {},                       // swap/replace an exercise (WP3.4e)
    onSupersetToggle: () => {},             // superset checkbox change (WP3.4g)
    onExecutionStyleClick: () => {},        // open execution-style picker (WP3.4d)
    updateSupersetActionButtons: () => {},  // superset action bar sync (WP3.4g)
    initializeSupersetActions: () => {},    // superset action bar init (WP3.4g)
    refreshPlan: () => {},                  // re-fetch + re-render the plan
};

/**
 * Inject the feature callbacks the table renderer and drag behavior depend on.
 * Called once by workout-plan.js at module load.
 * @param {Partial<typeof tableDeps>} deps
 */
export function configureWorkoutPlanTable(deps) {
    Object.assign(tableDeps, deps);
}

/**
 * Transform muscle display value based on current view mode (Simple/Advanced)
 * @param {string} value - Raw muscle value from database
 * @param {'primary'|'isolated'} type - Type of muscle field
 * @param {string} isolatedMuscles - Optional isolated muscles for this exercise (for scientific detail)
 * @returns {string} - Display value appropriate for current mode
 */
export function transformMuscleDisplay(value, type = 'primary', isolatedMuscles = null) {
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

/**
 * Updates the routine tabs based on available routines in the data
 * @param {Array} exercises - Array of exercise objects
 */
export function updateRoutineTabs(exercises) {
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

/**
 * Handle view mode change (Simple/Advanced)
 * Updates displayed muscle values in the table without re-fetching data
 */
export function handleViewModeChange(e) {
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
export function initializeRoutineTabs() {
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
    tableDeps.updateSupersetActionButtons();

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
        const thumbnailHtml = buildExerciseThumbnailHtml(exercise);

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
        appendExerciseVideoButton(row, exercise);

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
                tableDeps.onSwap(exercise.id, exercise.exercise);
            });
        }

        // Add click handler for superset checkbox
        const checkbox = row.querySelector('.superset-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                tableDeps.onSupersetToggle(e.target);
            });
        }

        // Add click handler for execution style badge
        const execStyleCell = row.querySelector('.execution-style-cell');
        if (execStyleCell) {
            execStyleCell.addEventListener('click', (e) => {
                e.stopPropagation();
                tableDeps.onExecutionStyleClick(exercise.id, exercise);
            });
        }

        tbody.appendChild(row);
    });

    // Initialize drag and drop after populating the table
    initializeDragAndDrop();

    // Initialize superset action buttons
    tableDeps.initializeSupersetActions();
}

/**
 * Updates the metadata cells in a row after a swap
 * @param {HTMLElement} row - The table row element
 * @param {Object} updatedData - The updated exercise data
 */
export function updateRowMetadata(row, updatedData) {
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
export function updateCachedExercise(exerciseId, updatedData) {
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
                await tableDeps.refreshPlan();
            } catch (error) {
                console.error('Error updating exercise order:', error);
                showToast(error.message || 'Failed to update exercise order', true);
                // Refresh the table to restore original order
                await tableDeps.refreshPlan();
            }
        }
    });
}
