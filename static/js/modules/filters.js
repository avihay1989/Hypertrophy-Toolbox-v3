import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';

const FILTERS_DEBUG = false;
const filtersDebugLog = (...args) => {
    if (FILTERS_DEBUG) {
        console.log(...args);
    }
};

// Debounce timer for filtering
let filterDebounceTimer = null;

/**
 * Update the visual active state of a filter dropdown
 * Adds 'filter-active' class when a value is selected, removes it otherwise
 * @param {HTMLSelectElement} select - The filter dropdown element
 */
function updateFilterActiveState(select) {
    if (select.value && select.value !== '') {
        select.classList.add('filter-active');
    } else {
        select.classList.remove('filter-active');
    }
}

/**
 * Initialize active state for all filter dropdowns on page load
 * This handles cases where filters are pre-selected (e.g., restored from previous state)
 */
function initializeFilterActiveStates() {
    const filterDropdowns = document.querySelectorAll('#filters-form select.filter-dropdown');
    filterDropdowns.forEach(select => {
        updateFilterActiveState(select);
    });
}

export async function filterExercises(preserveSelection = false) {
    try {
        const filters = {};
        const filterElements = document.querySelectorAll('#filters-form select');
        const exerciseDropdown = document.getElementById("exercise");
        
        filterElements.forEach(select => {
            // Exclude exercise dropdown and routine dropdown from filters sent to backend
            // Routine is handled separately - it's not a property of exercises
            const filterKey = select.dataset.filterKey || select.id;
            if (select.value && select.id !== 'exercise' && select.id !== 'routine') {
                filters[filterKey] = select.value;
            }
        });

    filtersDebugLog('DEBUG: Collected filters:', filters);

        // If no filters are selected, reload all exercises
        if (Object.keys(filters).length === 0) {
            try {
                const response = await api.get("/get_all_exercises", { showLoading: false, showErrorToast: false });
                const exercises = response.data !== undefined ? response.data : response;
                if (exerciseDropdown && Array.isArray(exercises)) {
                    updateExerciseDropdown(exercises, preserveSelection);
                }
            } catch (e) {
                console.error("Error fetching all exercises:", e);
            }
            return;
        }

        const response = await api.post("/filter_exercises", filters, { showLoading: false, showErrorToast: false });

        const exercises = response.data !== undefined ? response.data : response;
        updateExerciseDropdown(exercises, preserveSelection);
        
        // Show message about filtered results
        const filterCount = Object.keys(filters).length;
        const filterNames = Object.keys(filters).map(k => k.replace(/_/g, ' ')).join(', ');
        showToast(`Found ${exercises.length} exercise${exercises.length !== 1 ? 's' : ''} matching ${filterNames}`);
    } catch (error) {
        console.error("Error filtering exercises:", error);
        showToast("Failed to filter exercises", true);
    }
}

// Debounced version of filterExercises to avoid too many API calls
function debouncedFilterExercises() {
    // Clear existing timer
    if (filterDebounceTimer) {
        clearTimeout(filterDebounceTimer);
    }
    
    // Set new timer (300ms debounce)
    filterDebounceTimer = setTimeout(() => {
        filterExercises();
    }, 300);
}

export function initializeFilters() {
    // Add auto-filtering on change for all filter dropdowns
    // Use event delegation to catch changes from both native selects and enhanced dropdowns
    const workoutContainer = document.getElementById('workout');
    if (workoutContainer) {
        workoutContainer.addEventListener('change', function(event) {
            const select = event.target;
            
            // Only process filter dropdowns (not exercise dropdown or routine dropdown)
            // Check if it's a select element in the filters form
            if (select.tagName === 'SELECT' && 
                select.closest('#filters-form') && 
                select.classList.contains('filter-dropdown') &&
                select.id !== 'exercise' &&
                select.id !== 'routine') {  // Also exclude routine from auto-filtering
                
                // Update visual feedback - add/remove filter-active class
                updateFilterActiveState(select);
                
                // Auto-filter with debounce
                debouncedFilterExercises();
            }
        });
    }

    // Add clear filters button event listener
    const clearFiltersBtn = document.getElementById('clear-filters-btn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }

    // Initialize filter form submit handler
    const filterForm = document.getElementById('filters-form');
    if (filterForm) {
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            // Clear debounce and filter immediately
            if (filterDebounceTimer) {
                clearTimeout(filterDebounceTimer);
            }
            filterExercises();
        });
    }
    
    // Initialize active states for any pre-selected filters (e.g., restored from previous state)
    initializeFilterActiveStates();
    
    // Log initial exercise count to console for debugging
    const exerciseDropdown = document.getElementById("exercise");
    if (exerciseDropdown) {
        // Subtract 1 for the placeholder "Select Exercise" option
        const exerciseCount = exerciseDropdown.options.length - 1;
        console.log(`[Exercises] ${exerciseCount} exercises loaded and available for selection`);
        filtersDebugLog(`[Exercises] Total available: ${exerciseCount}`);
    }
}

async function clearFilters() {
    // Get all select dropdowns in the filters form
    const allSelects = document.querySelectorAll('#filters-form select');
    
    // Reset each dropdown to empty/default value and trigger change event
    allSelects.forEach(select => {
        select.value = '';
        // Remove filter-active class to reset visual state
        select.classList.remove('filter-active');
        // Manually dispatch change event to ensure enhanced dropdowns update
        select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    
    // Reset routine cascade selector if it exists
    const routineDropdown = document.getElementById('routine');
    if (routineDropdown) {
        routineDropdown.value = '';
        routineDropdown.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    // Reset cascade dropdowns (for new cascade selector)
    const cascadeEnv = document.getElementById('routine-env');
    const cascadeProgram = document.getElementById('routine-program');
    const cascadeDay = document.getElementById('routine-day');
    
    if (cascadeEnv) {
        cascadeEnv.value = '';
        cascadeEnv.dispatchEvent(new Event('change', { bubbles: true }));
    }
    if (cascadeProgram) {
        cascadeProgram.value = '';
        cascadeProgram.innerHTML = '<option value="">Select Program</option>';
        cascadeProgram.disabled = true;
    }
    if (cascadeDay) {
        cascadeDay.value = '';
        cascadeDay.innerHTML = '<option value="">Select Workout</option>';
        cascadeDay.disabled = true;
    }
    
    // Reset breadcrumb
    const breadcrumb = document.getElementById('routine-breadcrumb');
    if (breadcrumb) {
        breadcrumb.innerHTML = '<span class="breadcrumb-placeholder">Select environment to begin</span>';
        breadcrumb.classList.remove('has-selection');
    }
    
    // Reset connectors
    document.querySelectorAll('.cascade-connector').forEach(conn => {
        conn.classList.remove('active');
    });
    
    // Reset exercise dropdown if it exists
    const exerciseDropdown = document.getElementById('exercise');
    if (exerciseDropdown) {
        exerciseDropdown.value = '';
        exerciseDropdown.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    // Reload all exercises in the exercise dropdown
    try {
        const response = await fetch("/get_all_exercises");
        if (response.ok) {
            const exercises = await response.json();
            if (exerciseDropdown && Array.isArray(exercises)) {
                // Clear existing options
                exerciseDropdown.innerHTML = '<option value="">Select Exercise</option>';
                
                // Add all exercises
                exercises.forEach(exercise => {
                    if (exercise) {
                        const option = document.createElement("option");
                        option.value = exercise;
                        option.textContent = exercise;
                        exerciseDropdown.appendChild(option);
                    }
                });
                
                // Remove filter-applied class if it exists
                exerciseDropdown.classList.remove('filter-applied', 'filtered');
                
                // Trigger rebuild event for enhanced dropdown
                exerciseDropdown.dispatchEvent(new CustomEvent('wpdd-rebuild', { bubbles: true }));
            }
        }
    } catch (error) {
        console.error("Error reloading exercises:", error);
        showToast(error.message || "Failed to reload exercises", true);
    }
    
    // Show success toast notification
    showToast('Filters cleared successfully');
}

function updateExerciseDropdown(exercises, preserveSelection = false) {
    const exerciseDropdown = document.getElementById("exercise");
    if (!exerciseDropdown) return;

    // Store current selection if we want to preserve it
    const currentSelection = preserveSelection ? exerciseDropdown.value : '';

    exerciseDropdown.innerHTML = '<option value="">Select Exercise</option>';
    
    let selectionRestored = false;
    exercises.forEach(exercise => {
        const option = document.createElement("option");
        option.value = exercise;
        option.textContent = exercise;
        
        // Restore selection if it exists in the new list
        if (preserveSelection && exercise === currentSelection) {
            option.selected = true;
            selectionRestored = true;
        }
        
        exerciseDropdown.appendChild(option);
    });

    // Trigger rebuild of enhanced dropdown if it exists
    const enhancedContainer = exerciseDropdown.closest('.wpdd');
    if (enhancedContainer) {
        // Dispatch a custom event to trigger rebuild
        const rebuildEvent = new CustomEvent('wpdd-rebuild', { bubbles: true });
        exerciseDropdown.dispatchEvent(rebuildEvent);
    }

    // Add glow effect only if selection was not preserved (meaning filters changed results)
    if (!selectionRestored || !preserveSelection) {
        exerciseDropdown.classList.add('filter-applied');
        
        // Remove glow effect after 2 seconds
        setTimeout(() => {
            exerciseDropdown.classList.remove('filter-applied');
        }, 2000);
    }
}

export function initializeAdvancedFilters() {
    const advancedFilters = document.querySelectorAll('.advanced-filter');
    advancedFilters.forEach(filter => {
        filter.addEventListener('change', () => {
            const category = filter.dataset.category;
            const value = filter.value;
            updateFilteredView(category, value);
        });
    });
}

export function updateFilteredView(category, value) {
    const rows = document.querySelectorAll('tr[data-category]');
    rows.forEach(row => {
        if (!value || row.dataset.category === value) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

export function initializeSearchFilter() {
    const searchInput = document.getElementById('search-filter');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
}

// Add keyboard event handling for filters
export function initializeFilterKeyboardEvents() {
    const filterInputs = document.querySelectorAll('#filters-form select, #filters-form input');
    filterInputs.forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                filterExercises();
            }
        });
    });
}
