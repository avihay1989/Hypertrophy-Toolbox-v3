import { createVolumeChart, createProgressChart } from './charts.js';
import { fetchWeeklySummary, fetchSessionSummary } from './summary.js';
import { handleDateChange } from './workout-log.js';

/**
 * Add custom +/- buttons to number inputs for reliable increment/decrement
 * Native browser spinners can be unreliable across different browsers/platforms
 */
function addCustomSpinnerButtons(input) {
    // Don't add buttons if already added
    if (input.dataset.hasCustomSpinners === 'true') return;
    input.dataset.hasCustomSpinners = 'true';
    
    // Create wrapper for the input + buttons
    const wrapper = document.createElement('div');
    wrapper.className = 'number-input-wrapper';
    // Start hidden; the edit-click handler switches to inline-flex when the user opens the editor
    wrapper.style.cssText = 'display: none; align-items: center; gap: 2px;';
    
    // Insert wrapper in place of input
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    
    // Create minus button
    const minusBtn = document.createElement('button');
    minusBtn.type = 'button';
    minusBtn.className = 'number-spinner-btn number-spinner-minus';
    minusBtn.innerHTML = '−'; // Use Unicode minus for better click area
    minusBtn.style.cssText = `
        width: 26px; height: 26px; padding: 0; border: 1px solid #ccc;
        background: #f8f9fa; border-radius: 4px; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px; font-weight: bold; color: #495057; line-height: 1;
        user-select: none;
    `;
    
    // Create plus button
    const plusBtn = document.createElement('button');
    plusBtn.type = 'button';
    plusBtn.className = 'number-spinner-btn number-spinner-plus';
    plusBtn.innerHTML = '+'; // Use plain text for better click area
    plusBtn.style.cssText = minusBtn.style.cssText;
    
    // Insert buttons
    wrapper.insertBefore(minusBtn, input);
    wrapper.appendChild(plusBtn);
    
    // Get step from input or default to 1
    const step = parseFloat(input.step) || 1;
    // Default min to 0 to prevent negative numbers for workout data
    const min = input.min !== '' ? parseFloat(input.min) : 0;
    const max = input.max !== '' ? parseFloat(input.max) : null;
    
    // Set min attribute on input if not already set
    if (!input.hasAttribute('min')) {
        input.setAttribute('min', '0');
    }
    
    // Handler to change value
    function changeValue(delta) {
        let currentValue = parseFloat(input.value) || 0;
        let newValue = currentValue + delta;
        
        // Respect min/max - always prevent negative
        if (newValue < min) newValue = min;
        if (max !== null && newValue > max) newValue = max;
        
        input.value = newValue;
        
        // Trigger input and change events so handlers respond
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Keep input focused
        input.focus();
    }
    
    // Add click handlers
    minusBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        changeValue(-step);
    });
    
    plusBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        changeValue(step);
    });
    
    // Prevent blur when clicking buttons
    minusBtn.addEventListener('mousedown', (e) => e.preventDefault());
    plusBtn.addEventListener('mousedown', (e) => e.preventDefault());
}

export function initializeUIHandlers() {
    function showEditableText(inputElement, nextTextValue = null) {
        const cell = inputElement.closest('.editable');
        if (!cell) {
            return;
        }

        const text = cell.querySelector('.editable-text');
        const wrapper = cell.querySelector('.number-input-wrapper');

        if (text) {
            if (nextTextValue !== null) {
                text.textContent = nextTextValue === '' ? '--' : nextTextValue;
            }
            text.style.display = text.classList.contains('date-display') ? 'flex' : 'block';
        }

        inputElement.style.display = 'none';
        if (wrapper) {
            wrapper.style.display = 'none';
        }
    }

    // Handle editable fields
    document.querySelectorAll('.editable').forEach(cell => {
        cell.addEventListener('click', function(e) {
            // Don't trigger if clicking on the input or spinner buttons
            if (e.target.classList.contains('editable-input') || 
                e.target.classList.contains('number-spinner-btn') ||
                e.target.closest('.number-spinner-btn')) {
                return;
            }
            
            const input = this.querySelector('.editable-input');
            const text = this.querySelector('.editable-text');
            const wrapper = this.querySelector('.number-input-wrapper');
            
            if (input) {
                text.style.display = 'none';
                input.style.display = 'block';
                // Also show the wrapper if it exists (for number inputs with custom buttons)
                if (wrapper) {
                    wrapper.style.display = 'inline-flex';
                }
                input.focus();
                
                // For date inputs, open the picker immediately
                if (input.type === 'date' && typeof input.showPicker === 'function') {
                    try {
                        input.showPicker();
                    } catch (err) {
                        // Silently fail if not supported
                    }
                }
            }
        });
    });
    
    // Initialize date input change handlers
    document.querySelectorAll('.date-editable .date-input').forEach(input => {
        input.addEventListener('change', function() {
            const logId = this.dataset.logId;
            if (logId) {
                handleDateChange({ target: this }, logId);
            }
        });
    });

    // Handle clicking outside editable fields
    document.addEventListener('click', function(e) {
        // Don't hide if clicking on spinner buttons
        if (e.target.classList.contains('number-spinner-btn') || 
            e.target.closest('.number-spinner-btn')) {
            return;
        }
        
        if (!e.target.closest('.editable') && !e.target.classList.contains('editable-input')) {
            document.querySelectorAll('.editable-input').forEach(input => {
                input.style.display = 'none';
            });
            document.querySelectorAll('.editable-text').forEach(text => {
                // Use flex for date displays, block for others
                text.style.display = text.classList.contains('date-display') ? 'flex' : 'block';
            });
            // Also hide number input wrappers
            document.querySelectorAll('.number-input-wrapper').forEach(wrapper => {
                wrapper.style.display = 'none';
            });
        }
    });

    // Handle routine dropdown click state
    const routineDropdown = document.querySelector('.routine-dropdown');
    if (routineDropdown) {
        routineDropdown.addEventListener('click', function() {
            this.classList.add('clicked');
        });

        // Reset background when clicking outside
        document.addEventListener('click', function(event) {
            if (!routineDropdown.contains(event.target)) {
                routineDropdown.classList.remove('clicked');
            }
        });
    }

    initializeSummaryMethodHandlers();

    // Global flag for spinner interaction tracking
    let activeSpinnerInput = null;
    let globalBlurTimeout = null;
    
    // Debounce timers for spinner input updates (to avoid too many API calls)
    const inputDebounceTimers = new Map();
    
    // Global mouseup handler (only add once)
    document.addEventListener('mouseup', function() {
        setTimeout(() => {
            activeSpinnerInput = null;
        }, 50);
    });

    // Add validation for editable inputs (excluding date inputs which have their own handler)
    document.querySelectorAll('.editable-input:not(.date-input)').forEach(input => {
        // Combined input handler for validation and spinner interaction
        input.addEventListener('input', function() {
            // Validation
            const field = this.closest('[data-field]')?.dataset?.field;
            if (field) {
                const isValid = validateScoredValue(this.value, field);
                this.classList.toggle('is-invalid', !isValid);
                this.classList.toggle('is-valid', isValid);
            }
            // Value changed (possibly via spinner), cancel any pending hide
            if (globalBlurTimeout) {
                clearTimeout(globalBlurTimeout);
                globalBlurTimeout = null;
            }
            
            // For number inputs (spinners), debounce and trigger the update
            // This ensures spinner clicks actually save the value
            if (this.type === 'number' && typeof window.updateScoredValue === 'function') {
                const row = this.closest('tr[data-log-id]');
                const cell = this.closest('[data-field]');
                if (row && cell) {
                    const logId = row.dataset.logId;
                    const fieldName = cell.dataset.field;
                    const value = this.value;
                    
                    // Clear existing timer for this input
                    const timerKey = `${logId}-${fieldName}`;
                    if (inputDebounceTimers.has(timerKey)) {
                        clearTimeout(inputDebounceTimers.get(timerKey));
                    }
                    
                    // Debounce: wait 500ms after last input before saving
                    // This allows rapid spinner clicks without hammering the API
                    inputDebounceTimers.set(timerKey, setTimeout(() => {
                        window.updateScoredValue(logId, fieldName, value);
                        inputDebounceTimers.delete(timerKey);
                    }, 500));
                }
            }
        });
        
        // Mousedown on input (including spinners) - flag that interaction is happening
        input.addEventListener('mousedown', function() {
            activeSpinnerInput = this;
            // Clear any pending blur timeout
            if (globalBlurTimeout) {
                clearTimeout(globalBlurTimeout);
                globalBlurTimeout = null;
            }
        });

        // Auto-close on blur after focus actually leaves the editable control.
        // Number inputs keep the same path, but custom spinner buttons prevent blur while in use.
        input.addEventListener('blur', function() {
            const inputElement = this;
            if (globalBlurTimeout) {
                clearTimeout(globalBlurTimeout);
            }

            globalBlurTimeout = setTimeout(() => {
                const wrapper = inputElement.closest('.number-input-wrapper');
                const activeElement = document.activeElement;

                if (
                    document.activeElement === inputElement ||
                    activeSpinnerInput === inputElement ||
                    (wrapper && activeElement && wrapper.contains(activeElement))
                ) {
                    return;
                }

                showEditableText(inputElement, inputElement.value);
                globalBlurTimeout = null;
            }, 200);
        });

        if (input.type === 'number') {
            // For number inputs, add custom +/- buttons since native spinners can be unreliable
            addCustomSpinnerButtons(input);
        }
        
        // Add Enter key support to submit and close the input
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                // Trigger change event and blur to close the input
                this.dispatchEvent(new Event('change', { bubbles: true }));
                showEditableText(this, this.value);
                this.blur();
            } else if (e.key === 'Escape') {
                // Cancel editing on Escape - revert to original value
                e.preventDefault();
                const cell = this.closest('.editable');
                if (cell) {
                    const text = cell.querySelector('.editable-text');
                    // Reset input value to original text (don't save)
                    if (text && text.textContent.trim() !== 'Click to set' && 
                        text.textContent.trim() !== 'Click to set date' &&
                        text.textContent.trim() !== 'Click to edit' &&
                        text.textContent.trim() !== '--') {
                        this.value = text.textContent.trim();
                    }
                    // Show text, hide input and wrapper
                    showEditableText(this);
                }
                this.blur();
            }
        });
    });
}

export function initializeFormHandlers() {
    // Add Exercise button handler
    const addExerciseBtn = document.getElementById('add-exercise-btn');
    if (addExerciseBtn) {
        addExerciseBtn.addEventListener('click', () => {
            console.log('Add Exercise button clicked');
            // The actual addExercise function will be imported where needed
        });
    }

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

export function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

export function initializeDropdowns() {
    // Initialize all dropdowns
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        new bootstrap.Dropdown(dropdown);
    });
}

export function handleTableSort() {
    document.querySelectorAll('th[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const table = header.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const column = header.dataset.sort;
            const ascending = header.classList.toggle('sort-asc');

            const sortedRows = rows.sort((a, b) => {
                const aValue = a.querySelector(`td[data-${column}]`)?.textContent;
                const bValue = b.querySelector(`td[data-${column}]`)?.textContent;
                return ascending ? 
                    aValue.localeCompare(bValue) : 
                    bValue.localeCompare(aValue);
            });

            tbody.innerHTML = '';
            sortedRows.forEach(row => tbody.appendChild(row));
        });
    });
}

export function initializeDataTables() {
    // DataTables removed - using native table sorting instead
    // If you need advanced table features, consider a lightweight vanilla JS alternative
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        initializeTableSorting(table);
    });
}

function initializeTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable]');
    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            sortTable(table, index);
        });
    });
}

function sortTable(table, columnIndex) {
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
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();
        
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

export function initializeCharts() {
    const chartContainers = document.querySelectorAll('[data-chart]');
    chartContainers.forEach(container => {
        const chartType = container.dataset.chart;
        const chartData = JSON.parse(container.dataset.chartData || '{}');
        
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        switch (chartType) {
            case 'volume':
                createVolumeChart(canvas, chartData);
                break;
            case 'progress':
                createProgressChart(canvas, chartData);
                break;
        }
    });
}

export function initializeSummaryMethodHandlers() {
    const methodSelect = document.getElementById('summary-method');
    if (!methodSelect) return;

    methodSelect.addEventListener('change', (e) => {
        const method = e.target.value;
        const currentPath = window.location.pathname;
        
        if (currentPath === '/weekly_summary') {
            fetchWeeklySummary(method);
        } else if (currentPath === '/session_summary') {
            fetchSessionSummary(method);
        }
    });
}

function initializeSuggestionCards() {
    document.querySelectorAll('.suggestion-card').forEach(card => {
        const toggle = card.querySelector('.expand-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                card.classList.toggle('expanded');
                toggle.textContent = card.classList.contains('expanded') ? 'Show Less' : 'Show More';
            });
        }
    });
}

// Call this function when suggestions are loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeSuggestionCards();
}); 
