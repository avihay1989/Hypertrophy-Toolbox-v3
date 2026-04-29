import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';
import { openExerciseVideoModal } from './exercise-video-modal.js';

export function initializeWorkoutLog() {
    console.log('Initializing workout log');

    // Fix date input format
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const date = e.target.value;
            if (date === "None" || date === "") {
                e.target.value = new Date().toISOString().split('T')[0];
            }
        });
    });

    // Initialize progression checks
    initializeProgressionChecks();

    // Initialize editable cells
    initializeEditableCells();

    // Initialize filters
    initializeWorkoutLogFilters();

    // §5 — wire reference-video play buttons in server-rendered rows.
    initializeVideoPlayButtons();

    // Initialize simple table sorting
    const workoutLogTable = document.querySelector('.workout-log-table');
    if (workoutLogTable) {
        initializeSimpleTableSorting(workoutLogTable);
    }

    // Initialize collapse toggles for the import section
    initializeCollapseToggles();

    // Move modal to body for proper z-index stacking, THEN bind events
    moveModalToBody();

    // Bind the confirm clear log button click handler AFTER modal is moved
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
        bindClearLogButton();
    }, 100);
}

/**
 * §5 — Bind click handlers to per-row reference-video play buttons.
 * Rows are server-rendered Jinja (templates/workout_log.html); the button
 * carries data-video-id (may be empty/NULL) and data-exercise-name.
 */
function initializeVideoPlayButtons() {
    const buttons = document.querySelectorAll('.log-play-video-btn');
    buttons.forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const videoId = btn.dataset.videoId || null;
            const exerciseName = btn.dataset.exerciseName || '';
            openExerciseVideoModal(videoId, exerciseName, btn);
        });
    });
}

/**
 * Bind the confirm clear log button click handler
 */
function bindClearLogButton() {
    const confirmBtn = document.getElementById('confirm-clear-log-btn');
    console.log('bindClearLogButton: confirmBtn found:', !!confirmBtn);
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function(e) {
            console.log('Confirm button clicked!');
            e.preventDefault();
            confirmClearWorkoutLog();
        });
        console.log('Event listener attached to confirm button');
    }
}

/**
 * Move the clear log modal to body to ensure proper z-index stacking
 */
function moveModalToBody() {
    const modal = document.getElementById('clearLogModal');
    if (modal && modal.parentElement !== document.body) {
        document.body.appendChild(modal);
    }
}

/**
 * Initialize collapse toggle functionality for the import controls frame
 */
function initializeCollapseToggles() {
    const toggleButtons = document.querySelectorAll('.workout-log-controls-frame .collapse-toggle');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const frame = this.closest('.collapsible-frame');
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            const toggleText = this.querySelector('.toggle-text');
            
            // Toggle collapsed state
            frame.classList.toggle('collapsed');
            
            // Update aria-expanded
            this.setAttribute('aria-expanded', !isExpanded);
            
            // Update button text
            if (toggleText) {
                toggleText.textContent = isExpanded ? 'Show' : 'Hide';
            }
        });
    });
}

/**
 * Import exercises from the current workout plan into the workout log
 */
export async function importFromWorkoutPlan() {
    try {
        const importBtn = document.getElementById('import-from-plan-btn');
        if (importBtn) {
            importBtn.disabled = true;
            importBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Importing...';
        }

        const data = await api.post('/export_to_workout_log', {}, { showLoading: false, showErrorToast: false });

        showToast('success', data.message || 'Successfully imported workout plan');
        
        // Reload page to show new entries
        setTimeout(() => {
            window.location.reload();
        }, 1000);

    } catch (error) {
        logApiError('Error importing workout plan:', error);
        showToast(isHandledApiError(error) ? 'warning' : 'error', error.message || 'Failed to import workout plan');
        
        // Re-enable button on error
        const importBtn = document.getElementById('import-from-plan-btn');
        if (importBtn) {
            importBtn.disabled = false;
            importBtn.innerHTML = '<i class="fas fa-file-import me-2"></i> Import Current Workout Plan';
        }
    }
}

/**
 * Actually clear all entries from the workout log (called after modal confirmation)
 */
export async function confirmClearWorkoutLog() {
    console.log('confirmClearWorkoutLog called - starting clear process');
    
    try {
        // Get the clear button to update its state
        const clearBtn = document.getElementById('clear-log-btn');
        if (clearBtn) {
            clearBtn.disabled = true;
            clearBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Clearing...';
        }

        console.log('Making api request to /clear_workout_log');
        const data = await api.post('/clear_workout_log', {}, { showLoading: false, showErrorToast: false });
        console.log('Response data:', data);

        // Hide the modal
        const modalElement = document.getElementById('clearLogModal');
        if (modalElement && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }

        showToast('success', data.message || 'Workout log cleared successfully');
        
        // Reload page to reflect changes
        setTimeout(() => {
            window.location.reload();
        }, 1000);

    } catch (error) {
        console.error('Error clearing workout log:', error);
        showToast('error', error.message || 'Failed to clear workout log');
        
        // Re-enable button on error
        const clearBtn = document.getElementById('clear-log-btn');
        if (clearBtn) {
            clearBtn.disabled = false;
            clearBtn.innerHTML = '<i class="fas fa-eraser me-2"></i> Clear Log';
        }
    }
}

// Make functions globally available
window.importFromWorkoutPlan = importFromWorkoutPlan;
window.confirmClearWorkoutLog = confirmClearWorkoutLog;

function initializeSimpleTableSorting(table) {
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.title = 'Click to sort';
        header.addEventListener('click', () => {
            sortTableByColumn(table, index);
        });
    });
}

function sortTableByColumn(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    const isAscending = header.classList.contains('sort-asc');
    
    // Remove sort classes from all headers
    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add appropriate sort class
    header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
    
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex]?.textContent.trim() || '';
        const bValue = b.cells[columnIndex]?.textContent.trim() || '';
        
        // Try to parse as number
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? bNum - aNum : aNum - bNum;
        }
        
        // String comparison
        return isAscending ? 
            bValue.localeCompare(aValue) : 
            aValue.localeCompare(bValue);
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

export function initializeProgressionChecks() {
    // Initialize progression status for all log entries
    document.querySelectorAll('[data-log-id]').forEach(entry => {
        const logId = entry.dataset.logId;
        checkProgressiveOverload(logId);
    });

    // Initialize date inputs
    initializeDateInputs();
}

function initializeDateInputs() {
    document.querySelectorAll('.progression-date').forEach(dateInput => {
        // Set default date to today if empty
        if (!dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }

        // Add change handler
        dateInput.addEventListener('change', (e) => {
            const logId = e.target.closest('[data-log-id]').dataset.logId;
            updateProgressionDate(logId, e.target.value);
        });
    });
}

export async function updateProgressionDate(logId, newDate) {
    try {
        const response = await api.post('/update_progression_date', {
            id: logId,
            date: newDate
        });

        showToast('success', response.message || 'Progression date updated successfully');

        // Update UI
        const dateCell = document.querySelector(`tr[data-log-id="${logId}"] .progression-date`);
        if (dateCell) {
            dateCell.textContent = newDate || 'Not set';
        }

        // Update progression status
        checkProgressiveOverload(logId);

    } catch (error) {
        // Error already logged and toast shown by fetch wrapper
        console.error('Error updating progression date:', error);
    }
}

export async function updateProgressionStatus(logId) {
    try {
        const response = await api.get(`/check_progression/${logId}`);

        const badge = document.querySelector(`tr[data-log-id="${logId}"] .progression-badge`);
        if (badge && response.data) {
            badge.className = `badge ${response.data.is_progressive ? 'bg-success' : 'bg-warning'}`;
            badge.textContent = response.data.status;
        }

    } catch (error) {
        // Error already logged and toast shown by fetch wrapper
        console.error('Error checking progression:', error);
    }
}

export async function updateScoredValue(logId, field, value) {
    try {
        const response = await api.post('/update_workout_log', {
            id: logId,
            updates: {
                [field]: value === '' ? null : value
            }
        });

        // Update the display text
        const row = document.querySelector(`tr[data-log-id="${logId}"]`);
        const cell = row.querySelector(`[data-field="${field}"]`);
        if (cell) {
            const display = cell.querySelector('.editable-text');
            if (display) {
                display.textContent = value || '--';
            }
            
            // Update progression indicator for this cell
            updateProgressionIndicator(row, field, value);
        }

        // Update badge status
        const badge = row.querySelector('.badge');
        if (badge) {
            // Get all the values
            const planned_rir = parseFloat(row.querySelector('[data-field="planned_rir"]')?.textContent) || 0;
            const planned_rpe = parseFloat(row.querySelector('[data-field="planned_rpe"]')?.textContent) || 0;
            const planned_min_reps = parseFloat(row.querySelector('[data-field="planned_min_reps"]')?.textContent) || 0;
            const planned_max_reps = parseFloat(row.querySelector('[data-field="planned_max_reps"]')?.textContent) || 0;
            const planned_weight = parseFloat(row.querySelector('[data-field="planned_weight"]')?.textContent) || 0;

            const scored_rir = parseFloat(row.querySelector('[data-field="scored_rir"] .editable-text')?.textContent) || 0;
            const scored_rpe = parseFloat(row.querySelector('[data-field="scored_rpe"] .editable-text')?.textContent) || 0;
            const scored_min_reps = parseFloat(row.querySelector('[data-field="scored_min_reps"] .editable-text')?.textContent) || 0;
            const scored_max_reps = parseFloat(row.querySelector('[data-field="scored_max_reps"] .editable-text')?.textContent) || 0;
            const scored_weight = parseFloat(row.querySelector('[data-field="scored_weight"] .editable-text')?.textContent) || 0;

            const isProgressive = (
                (scored_rir && planned_rir && scored_rir < planned_rir) ||
                (scored_rpe && planned_rpe && scored_rpe > planned_rpe) ||
                (scored_min_reps && planned_min_reps && scored_min_reps > planned_min_reps) ||
                (scored_max_reps && planned_max_reps && scored_max_reps > planned_max_reps) ||
                (scored_weight && planned_weight && scored_weight > planned_weight)
            );

            badge.className = `badge ${isProgressive ? 'bg-success' : 'bg-warning'}`;
            badge.textContent = isProgressive ? 'Achieved' : 'Pending';
        }

        showToast('Value updated successfully');
    } catch (error) {
        console.error('Error updating value:', error);
        showToast('error', 'Failed to update value');
    }
}

/**
 * Update the progression indicator icon for a specific field after value change
 */
function updateProgressionIndicator(row, field, scoredValue) {
    // Get the planned field name by removing 'scored_' prefix
    const plannedField = field.replace('scored_', 'planned_');
    const plannedCell = row.querySelector(`[data-field="${plannedField}"]`);
    const scoredCell = row.querySelector(`[data-field="${field}"]`);
    
    if (!plannedCell || !scoredCell) return;
    
    const plannedValue = parseFloat(plannedCell.textContent);
    const scored = parseFloat(scoredValue);
    
    // Remove existing indicator
    const existingIndicator = scoredCell.querySelector('.progression-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    // Don't add indicator if no scored value
    if (!scoredValue || isNaN(scored) || isNaN(plannedValue)) return;
    
    // Create new indicator
    const indicator = document.createElement('i');
    indicator.classList.add('fas', 'progression-indicator');
    
    // Determine the comparison logic based on field type
    let isImproved, isSame, diff;
    
    if (field === 'scored_rir') {
        // For RIR, LOWER is BETTER
        isImproved = scored < plannedValue;
        isSame = scored === plannedValue;
        diff = plannedValue - scored;
        
        if (isImproved) {
            indicator.classList.add('fa-arrow-up', 'text-success');
            indicator.title = `Pushed harder! (RIR -${diff})`;
        } else if (isSame) {
            indicator.classList.add('fa-equals', 'text-warning');
            indicator.title = 'Met target RIR';
        } else {
            indicator.classList.add('fa-arrow-down', 'text-danger');
            indicator.title = `Easier than planned (RIR +${scored - plannedValue})`;
        }
    } else if (field === 'scored_rpe') {
        // For RPE, HIGHER means more effort (better)
        isImproved = scored > plannedValue;
        isSame = scored === plannedValue;
        diff = (scored - plannedValue).toFixed(1);
        
        if (isImproved) {
            indicator.classList.add('fa-arrow-up', 'text-success');
            indicator.title = `Higher effort! (+${diff})`;
        } else if (isSame) {
            indicator.classList.add('fa-equals', 'text-warning');
            indicator.title = 'Met target RPE';
        } else {
            indicator.classList.add('fa-arrow-down', 'text-danger');
            indicator.title = `Lower effort (${diff})`;
        }
    } else if (field === 'scored_weight') {
        // For weight, HIGHER is BETTER
        isImproved = scored > plannedValue;
        isSame = scored === plannedValue;
        diff = (scored - plannedValue).toFixed(1);
        
        if (isImproved) {
            indicator.classList.add('fa-arrow-up', 'text-success');
            indicator.title = `Weight increased! (+${diff}kg)`;
        } else if (isSame) {
            indicator.classList.add('fa-equals', 'text-warning');
            indicator.title = 'Same weight';
        } else {
            indicator.classList.add('fa-arrow-down', 'text-danger');
            indicator.title = `Weight decreased (${diff}kg)`;
        }
    } else {
        // For reps (min/max), HIGHER is BETTER
        isImproved = scored > plannedValue;
        isSame = scored === plannedValue;
        diff = scored - plannedValue;
        
        if (isImproved) {
            indicator.classList.add('fa-arrow-up', 'text-success');
            indicator.title = `Above target! (+${diff})`;
        } else if (isSame) {
            indicator.classList.add('fa-equals', 'text-warning');
            indicator.title = 'Met target';
        } else {
            indicator.classList.add('fa-arrow-down', 'text-danger');
            indicator.title = `Below target (${diff})`;
        }
    }
    
    // Add indicator to the container
    const container = scoredCell.querySelector('.scored-value-container');
    if (container) {
        container.appendChild(indicator);
    }
}

export function validateScoredValue(value, field) {
    if (value === '') return true;
    
    const num = Number(value);
    if (isNaN(num)) return false;

    switch (field) {
        case 'scored_sets':
            return num > 0 && num <= 10;
        case 'scored_reps':
            return num > 0 && num <= 100;
        case 'scored_weight':
            return num >= 0 && num <= 1000;
        case 'scored_rir':
            return num >= 0 && num <= 5;
        case 'scored_rpe':
            return num >= 0 && num <= 10;
        default:
            return true;
    }
}

export function checkProgressiveOverload(logId) {
    const row = document.querySelector(`tr[data-log-id="${logId}"]`);
    if (!row) {
        console.error('Row not found for log ID:', logId);
        return;
    }

    // Get planned values
    const planned_rir = parseFloat(row.querySelector('[data-field="planned_rir"]')?.textContent) || 0;
    const planned_rpe = parseFloat(row.querySelector('[data-field="planned_rpe"]')?.textContent) || 0;
    const planned_min_reps = parseFloat(row.querySelector('[data-field="planned_min_reps"]')?.textContent) || 0;
    const planned_max_reps = parseFloat(row.querySelector('[data-field="planned_max_reps"]')?.textContent) || 0;
    const planned_weight = parseFloat(row.querySelector('[data-field="planned_weight"]')?.textContent) || 0;

    // Get scored values
    const scored_rir = parseFloat(row.querySelector('[data-field="scored_rir"] .editable-text')?.textContent) || 0;
    const scored_rpe = parseFloat(row.querySelector('[data-field="scored_rpe"] .editable-text')?.textContent) || 0;
    const scored_min_reps = parseFloat(row.querySelector('[data-field="scored_min_reps"] .editable-text')?.textContent) || 0;
    const scored_max_reps = parseFloat(row.querySelector('[data-field="scored_max_reps"] .editable-text')?.textContent) || 0;
    const scored_weight = parseFloat(row.querySelector('[data-field="scored_weight"] .editable-text')?.textContent) || 0;

    const isProgressive = (
        (scored_rir && planned_rir && scored_rir < planned_rir) ||
        (scored_rpe && planned_rpe && scored_rpe > planned_rpe) ||
        (scored_min_reps && planned_min_reps && scored_min_reps > planned_min_reps) ||
        (scored_max_reps && planned_max_reps && scored_max_reps > planned_max_reps) ||
        (scored_weight && planned_weight && scored_weight > planned_weight)
    );

    const badge = row.querySelector('.badge');
    if (badge) {
        badge.className = `badge ${isProgressive ? 'bg-success' : 'bg-warning'}`;
        badge.textContent = isProgressive ? 'Achieved' : 'Pending';
    }
}

export function initializeEditableCells() {
    document.querySelectorAll('.editable-cell').forEach(cell => {
        const input = cell.querySelector('input');
        const display = cell.querySelector('.display-value');

        if (input && display) {
            input.addEventListener('change', async () => {
                try {
                    const logId = cell.dataset.logId;
                    const field = cell.dataset.field;
                    const value = input.value;

                    await updateScoredValue(logId, field, value);
                    display.textContent = value || 'Click to edit';
                    input.style.display = 'none';
                    display.style.display = 'block';
                } catch (error) {
                    console.error('Error updating value:', error);
                    showToast('error', 'Failed to update value');
                }
            });
        }
    });
}

export function initializeWorkoutLogFilters() {
    const dateFilter = document.getElementById('date-filter');
    const routineFilter = document.getElementById('routine-filter');
    
    if (dateFilter) {
        dateFilter.addEventListener('change', filterWorkoutLogs);
    }
    if (routineFilter) {
        routineFilter.addEventListener('change', filterWorkoutLogs);
    }
}

async function filterWorkoutLogs() {
    try {
        const date = document.getElementById('date-filter')?.value;
        const routine = document.getElementById('routine-filter')?.value;

        const response = await api.post('/filter_workout_logs', { date, routine }, { showLoading: false, showErrorToast: false });
        
        // response.data contains the logs array
        const data = response.data !== undefined ? response.data : response;
        updateWorkoutLogTable(data);
    } catch (error) {
        console.error('Error filtering workout logs:', error);
        showToast('error', 'Failed to filter workout logs');
    }
}

function updateWorkoutLogTable(data) {
    const tbody = document.querySelector('#workout-log-table tbody');
    if (!tbody) return;

    tbody.innerHTML = data.length ? 
        data.map(log => createWorkoutLogRow(log)).join('') :
        '<tr><td colspan="8" class="text-center">No workout logs found</td></tr>';
}

function createWorkoutLogRow(log) {
    return `
        <tr data-log-id="${log.id}">
            <td>${log.date}</td>
            <td>${log.routine}</td>
            <td>${log.exercise}</td>
            <td class="editable-cell" data-field="scored_sets">
                <span class="editable-text">${log.scored_sets || 'Click to edit'}</span>
                <input type="number" class="editable-input form-control input-calm-inset"
                    value="${log.scored_sets || ''}" style="display: none;">
            </td>
            <td class="editable-cell" data-field="scored_reps">
                <span class="editable-text">${log.scored_reps || 'Click to edit'}</span>
                <input type="number" class="editable-input form-control input-calm-inset"
                    value="${log.scored_reps || ''}" style="display: none;">
            </td>
            <td class="editable-cell" data-field="scored_weight">
                <span class="editable-text">${log.scored_weight || 'Click to edit'}</span>
                <input type="number" class="editable-input form-control input-calm-inset"
                    value="${log.scored_weight || ''}" style="display: none;">
            </td>
            <td>
                <span class="badge ${log.progression_status === 'Achieved' ? 'bg-success' : 'bg-warning'}">
                    ${log.progression_status}
                </span>
            </td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deleteWorkoutLog(${log.id})">
                    Delete
                </button>
            </td>
        </tr>
    `;
}

export async function checkProgressionStatus(logId) {
    const row = document.querySelector(`tr[data-log-id="${logId}"]`);
    if (!row) return;

    const progressionBadge = row.querySelector('.progression-badge');
    if (!progressionBadge) return;

    try {
        const data = await api.get(`/check_progression/${logId}`, { showLoading: false, showErrorToast: false });
        const result = data.data !== undefined ? data.data : data;
        
        progressionBadge.className = `badge ${result.achieved ? 'bg-success' : 'bg-warning'}`;
        progressionBadge.textContent = result.achieved ? 'Achieved' : 'Pending';
    } catch (error) {
        console.error('Error checking progression:', error);
        showToast('error', 'Failed to check progression status');
    }
}

export async function deleteWorkoutLog(logId) {
    try {
        await api.post('/delete_workout_log', { id: logId }, { showLoading: false, showErrorToast: false });

        // Remove the row from the table
        const row = document.querySelector(`tr[data-log-id="${logId}"]`);
        if (row) {
            row.remove();
        }

        showToast('success', 'Log entry deleted successfully');
    } catch (error) {
        console.error('Error:', error);
        showToast('error', error.message || 'Failed to delete log entry');
    }
}

/**
 * Format Date object to DD-MM-YY for display
 * @param {Date} date - Date object
 * @returns {string} - Date string in DD-MM-YY format
 */
function formatToDDMMYY(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = String(date.getFullYear()).slice(-2);
    return `${day}-${month}-${year}`;
}

export async function handleDateChange(event, logId) {
    try {
        const inputValue = event.target.value; // Native date input gives YYYY-MM-DD
        const input = event.target;
        
        // If logId not provided, get from data attribute
        const id = logId || input.dataset.logId;
        
        let displayDate = '';
        
        // Validate date if provided
        if (inputValue && inputValue.trim() !== '') {
            const dateObj = new Date(inputValue);
            const year = dateObj.getFullYear();
            
            if (isNaN(dateObj.getTime()) || year < 2020 || year > 2099) {
                showToast('error', 'Please select a valid date (2020-2099)');
                return;
            }
            
            displayDate = formatToDDMMYY(dateObj);
        }
        
        await api.post('/update_progression_date', {
            id: id,
            date: inputValue // Send YYYY-MM-DD format to backend
        }, { showLoading: false, showErrorToast: false });

        // Update the display text and hide the input
        const cell = input.closest('.editable');
        const display = cell.querySelector('.editable-text');
        if (display) {
            if (displayDate) {
                display.innerHTML = displayDate;
            } else {
                // Show calendar icon when no date is set
                display.innerHTML = '<i class="fas fa-calendar-alt date-icon"></i>';
            }
            display.style.display = 'flex';
        }
        
        // Hide the input after successful update
        input.style.display = 'none';

        // Get the row and update badge status
        const row = document.querySelector(`tr[data-log-id="${id}"]`);
        const badge = row?.querySelector('.badge');
        if (badge) {
            // Get all the values
            const planned_rir = parseFloat(row.querySelector('[data-field="planned_rir"]')?.textContent) || 0;
            const planned_rpe = parseFloat(row.querySelector('[data-field="planned_rpe"]')?.textContent) || 0;
            const planned_min_reps = parseFloat(row.querySelector('[data-field="planned_min_reps"]')?.textContent) || 0;
            const planned_max_reps = parseFloat(row.querySelector('[data-field="planned_max_reps"]')?.textContent) || 0;
            const planned_weight = parseFloat(row.querySelector('[data-field="planned_weight"]')?.textContent) || 0;

            const scored_rir = parseFloat(row.querySelector('[data-field="scored_rir"] .editable-text')?.textContent) || 0;
            const scored_rpe = parseFloat(row.querySelector('[data-field="scored_rpe"] .editable-text')?.textContent) || 0;
            const scored_min_reps = parseFloat(row.querySelector('[data-field="scored_min_reps"] .editable-text')?.textContent) || 0;
            const scored_max_reps = parseFloat(row.querySelector('[data-field="scored_max_reps"] .editable-text')?.textContent) || 0;
            const scored_weight = parseFloat(row.querySelector('[data-field="scored_weight"] .editable-text')?.textContent) || 0;

            const isProgressive = (
                (scored_rir && planned_rir && scored_rir < planned_rir) ||
                (scored_rpe && planned_rpe && scored_rpe > planned_rpe) ||
                (scored_min_reps && planned_min_reps && scored_min_reps > planned_min_reps) ||
                (scored_max_reps && planned_max_reps && scored_max_reps > planned_max_reps) ||
                (scored_weight && planned_weight && scored_weight > planned_weight)
            );

            badge.className = `badge ${isProgressive ? 'bg-success' : 'bg-warning'}`;
            badge.textContent = isProgressive ? 'Achieved' : 'Pending';
        }

        showToast('success', 'Progression date updated successfully');
    } catch (error) {
        console.error('Error updating progression date:', error);
        showToast('error', 'Failed to update progression date');
    }
} 
