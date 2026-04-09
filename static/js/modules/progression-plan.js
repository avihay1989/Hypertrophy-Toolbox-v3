import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';

// Store flatpickr instance
let goalDatePicker = null;

function unwrapProgressionResponseData(response) {
    if (response && typeof response === 'object' && 'data' in response) {
        return response.data;
    }

    return response;
}

function getProgressionSuccessMessage(response, fallbackMessage) {
    if (response && typeof response === 'object' && typeof response.message === 'string' && response.message.trim()) {
        return response.message;
    }

    return fallbackMessage;
}

export function initializeProgressionPlan() {
    const exerciseSelect = document.getElementById('exerciseSelect');
    const suggestionsContainer = document.getElementById('suggestionsContainer');
    const suggestionsList = document.getElementById('suggestionsList');
    const goalModalElement = document.getElementById('goalSettingModal');
    const goalModal = new bootstrap.Modal(goalModalElement, {
        keyboard: true,
        backdrop: false,
        focus: true,
    });
    
    // Store the element that had focus before the modal was opened
    let previousActiveElement;
    
    // Handle modal show
    goalModalElement.addEventListener('show.bs.modal', function () {
        // Store the current focus
        previousActiveElement = document.activeElement;
    });
    
    // Reset form when modal is hidden
    goalModalElement.addEventListener('hidden.bs.modal', function () {
        document.getElementById('goalForm').reset();
        const inputs = document.querySelectorAll('#goalForm input:not([type="hidden"])');
        inputs.forEach(input => {
            input.disabled = false;
        });
        // Clear the flatpickr date
        if (goalDatePicker) {
            goalDatePicker.clear();
        }
        // Restore focus to the previous element
        if (previousActiveElement) {
            previousActiveElement.focus();
        }
    });
    
    // Enable form inputs when modal is shown
    goalModalElement.addEventListener('shown.bs.modal', function () {
        const currentValueInput = document.getElementById('currentValue');
        const targetValueInput = document.getElementById('targetValue');
        if (document.getElementById('goalType').value !== 'technique') {
            currentValueInput.disabled = false;
            targetValueInput.disabled = false;
        }
        // Set focus to the first input field
        if (!currentValueInput.disabled) {
            currentValueInput.focus();
        } else {
            document.getElementById('goalDate').focus();
        }
    });
    
    // Add event listener for closing modal
    document.getElementById('closeGoalModal').addEventListener('click', () => {
        goalModal.hide();
    });
    
    // Add keyboard event listener for ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && goalModalElement.classList.contains('show')) {
            goalModal.hide();
        }
    });
    
    // Initialize flatpickr for goal date with DD-MM-YYYY format
    const goalDateInput = document.getElementById('goalDate');
    if (goalDateInput && typeof flatpickr !== 'undefined') {
        goalDatePicker = flatpickr(goalDateInput, {
            dateFormat: 'd-m-Y',
            minDate: 'today',
            allowInput: true,
            clickOpens: true,
            disableMobile: true // Force desktop picker on all devices
        });
    }
    
    console.log('Initializing progression plan with elements:', {
        exerciseSelect,
        suggestionsContainer,
        suggestionsList,
        goalModal
    });
    
    if (!exerciseSelect) {
        console.error('exerciseSelect is null!');
        return;
    }
    
    // Add event listeners
    exerciseSelect.addEventListener('click', () => {
        console.log('Exercise select clicked');
    });
    
    exerciseSelect.addEventListener('change', handleExerciseChange);
    
    // Add event listener for goal setting buttons
    document.addEventListener('click', async function(e) {
        if (e.target.classList.contains('set-goal-btn')) {
            console.log('Goal button clicked:', e.target);
            const rawGoalType = e.target.dataset.goalType;
            const exercise = e.target.dataset.exercise;
            const prefilledCurrentValue = e.target.dataset.currentValue;
            const prefilledTargetValue = e.target.dataset.targetValue;
            
            // Map specialized goal types to base types for storage and API calls
            const goalTypeMapping = {
                'double_progression_weight': 'weight',
                'double_progression_reps': 'reps',
                'reduce_weight': 'weight',
                'maintain_progress': 'reps',
                'weight': 'weight',
                'reps': 'reps',
                'sets': 'sets',
                'technique': 'technique'
            };
            const goalType = goalTypeMapping[rawGoalType] || rawGoalType;
            console.log('Goal type:', rawGoalType, '-> mapped to:', goalType, 'Exercise:', exercise);
            console.log('Prefilled values - current:', prefilledCurrentValue, 'target:', prefilledTargetValue);
            
            // Pre-fill current values based on goal type
            const currentValueInput = document.getElementById('currentValue');
            const targetValueInput = document.getElementById('targetValue');
            
            // Default to 4 weeks from now using flatpickr
            const fourWeeksFromNow = new Date();
            fourWeeksFromNow.setDate(fourWeeksFromNow.getDate() + 28);
            if (goalDatePicker) {
                goalDatePicker.setDate(fourWeeksFromNow, true);
            }
            
            // Use pre-filled values if available, otherwise fetch from API
            if (goalType !== 'technique') {
                // Check for valid pre-filled values (not empty, 'null', or undefined)
                const hasValidCurrentValue = prefilledCurrentValue && prefilledCurrentValue !== '' && prefilledCurrentValue !== 'null';
                const hasValidTargetValue = prefilledTargetValue && prefilledTargetValue !== '' && prefilledTargetValue !== 'null';
                
                if (hasValidCurrentValue && hasValidTargetValue) {
                    // Use the pre-calculated values from the suggestion
                    console.log('Using prefilled values from suggestion');
                    currentValueInput.value = prefilledCurrentValue;
                    targetValueInput.value = prefilledTargetValue;
                } else {
                    // Fallback: Fetch current value from workout history
                    try {
                        console.log(`Fetching current value for ${exercise} (${goalType})`);
                        const response = await api.post('/get_current_value', 
                            { exercise, goal_type: goalType }, 
                            { showLoading: false, showErrorToast: false }
                        );
                        
                        const data = unwrapProgressionResponseData(response);
                        console.log('Received current value data:', data);
                        
                        if (data && typeof data === 'object' && data.error) {
                            throw new Error(data.error);
                        }
                        
                        // Ensure we're getting a number
                        const currentValue = parseFloat(data.current_value) || 0;
                        console.log('Parsed current value:', currentValue);
                        currentValueInput.value = data.current_value;
                        
                        // Update target value based on current value using suggested increments
                        switch(goalType) {
                            case 'reps':
                                // Suggest adding 2 reps
                                targetValueInput.value = currentValue + 2;
                                break;
                            case 'weight':
                                // Use same increment logic as suggestion cards: 2.5kg if < 20, else 5kg
                                const weightIncrement = currentValue < 20 ? 2.5 : 5;
                                targetValueInput.value = currentValue + weightIncrement;
                                break;
                            case 'sets':
                                // Suggest adding 1 set
                                targetValueInput.value = currentValue + 1;
                                break;
                        }
                    } catch (error) {
                        console.error('Error fetching current value:', error);
                        currentValueInput.value = '0';
                        targetValueInput.value = goalType === 'reps' ? '2' : 
                                               goalType === 'weight' ? '5' : 
                                               goalType === 'sets' ? '1' : '0';
                    }
                }
            }
            
            // Customize modal based on goal type
            const modalTitle = document.querySelector('.modal-title');
            switch(goalType) {
                case 'technique':
                    modalTitle.textContent = 'Set Technique Goal';
                    currentValueInput.value = 'N/A';
                    targetValueInput.value = 'N/A';
                    currentValueInput.disabled = true;
                    targetValueInput.disabled = true;
                    break;
                case 'reps':
                    modalTitle.textContent = 'Set Repetition Goal';
                    currentValueInput.disabled = false;
                    targetValueInput.disabled = false;
                    // Keep the already calculated target value (current + 2 reps)
                    break;
                case 'weight':
                    modalTitle.textContent = 'Set Weight Goal';
                    currentValueInput.disabled = false;
                    targetValueInput.disabled = false;
                    // Keep the already calculated target value (current + increment)
                    break;
                case 'sets':
                    modalTitle.textContent = 'Set Volume Goal';
                    currentValueInput.disabled = false;
                    targetValueInput.disabled = false;
                    // Keep the already calculated target value (current + 1 set)
                    break;
            }
            
            document.getElementById('goalType').value = goalType;
            document.getElementById('exerciseName').value = exercise;
            
            goalModal.show();
        }
    });
    
    // Handle goal saving
    document.getElementById('saveGoal').addEventListener('click', async function(e) {
        e.preventDefault();
        try {
            // Get the date in YYYY-MM-DD format for backend
            let goalDateValue = '';
            if (goalDatePicker && goalDatePicker.selectedDates.length > 0) {
                const selectedDate = goalDatePicker.selectedDates[0];
                const year = selectedDate.getFullYear();
                const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
                const day = String(selectedDate.getDate()).padStart(2, '0');
                goalDateValue = `${year}-${month}-${day}`;
            }
            
            const formData = {
                exercise: document.getElementById('exerciseName').value,
                goal_type: document.getElementById('goalType').value,
                current_value: document.getElementById('currentValue').value,
                target_value: document.getElementById('targetValue').value,
                goal_date: goalDateValue
            };
            
            // Validate form data
            if (!formData.exercise || !formData.goal_type || !formData.goal_date) {
                throw new Error('Please fill in all required fields');
            }
            
            if (formData.goal_type !== 'technique' && (!formData.current_value || !formData.target_value)) {
                throw new Error('Please enter current and target values');
            }
            
            console.log('Saving goal:', formData);
            
            const response = await api.post('/save_progression_goal', formData, { showErrorToast: false });
            
            goalModal.hide();
            showToast('success', getProgressionSuccessMessage(response, 'Goal saved successfully'));
            setTimeout(() => {
                location.reload();
            }, 300);
        } catch (error) {
            console.error('Error saving goal:', error);
            showToast('Failed to save goal: ' + error.message, true);
        }
    });
    
    async function handleExerciseChange() {
        console.log('Exercise select changed');
        const exercise = this.value;
        console.log('Selected exercise:', exercise);
        
        if (!exercise) {
            suggestionsContainer.style.display = 'none';
            return;
        }
        
        try {
            console.log('Sending request for exercise:', exercise);
            
            const response = await api.post('/get_exercise_suggestions', 
                { exercise }, 
                { showLoading: false, showErrorToast: false }
            );
            
            console.log('Response received:', response);
            
            const suggestions = unwrapProgressionResponseData(response);
            console.log('Suggestions data:', suggestions);
            
            if (!Array.isArray(suggestions)) {
                throw new Error('Invalid suggestions data received');
            }
            
            displaySuggestions(suggestions, exercise);
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            suggestionsList.innerHTML = `
                <div class="alert alert-danger">
                    Error loading suggestions: ${error.message}
                </div>
            `;
            suggestionsContainer.style.display = 'block';
        }
    }
    
    function displaySuggestions(suggestions, exercise) {
        console.log('Displaying suggestions for:', exercise);
        suggestionsList.innerHTML = '';
        
        if (!suggestions || suggestions.length === 0) {
            suggestionsList.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-info">
                        No suggestions available for this exercise yet.
                    </div>
                </div>
            `;
            suggestionsContainer.style.display = 'block';
            return;
        }
        
        suggestions.forEach(suggestion => {
            const card = document.createElement('div');
            card.className = 'col-md-6 col-lg-3';
            // Include current_value and suggested_value as data attributes if available
            // Check for both undefined and null to handle cases where Python None becomes JSON null
            const currentValue = (suggestion.current_value !== undefined && suggestion.current_value !== null) ? suggestion.current_value : '';
            const suggestedValue = (suggestion.suggested_value !== undefined && suggestion.suggested_value !== null) ? suggestion.suggested_value : '';
            card.innerHTML = `
                <div class="card suggestion-card" data-goal-type="${suggestion.type}">
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title">${suggestion.title}</h5>
                        <p class="card-text">${suggestion.description}</p>
                        <button class="btn btn-primary set-goal-btn mt-auto" 
                                data-goal-type="${suggestion.type}"
                                data-exercise="${exercise}"
                                data-current-value="${currentValue}"
                                data-target-value="${suggestedValue}">
                            ${suggestion.action}
                        </button>
                    </div>
                </div>
            `;
            suggestionsList.appendChild(card);
            console.log('Added suggestion card:', suggestion.type);
        });
        
        suggestionsContainer.style.display = 'block';
    }
    
    // Handle focus trap in modal
    goalModalElement.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const focusableElements = goalModalElement.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstFocusableElement = focusableElements[0];
            const lastFocusableElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey) { // Shift + Tab
                if (document.activeElement === firstFocusableElement) {
                    lastFocusableElement.focus();
                    e.preventDefault();
                }
            } else { // Tab
                if (document.activeElement === lastFocusableElement) {
                    firstFocusableElement.focus();
                    e.preventDefault();
                }
            }
        }
    });
    
    // Delete confirmation modal setup
    const deleteModalElement = document.getElementById('deleteGoalModal');
    const deleteModal = new bootstrap.Modal(deleteModalElement, {
        keyboard: true,
        backdrop: true,
        focus: true,
    });
    let pendingDeleteGoalId = null;
    let pendingDeleteButton = null;

    // Handle goal deletion - show modal
    document.addEventListener('click', function(e) {
        if (e.target.closest('.delete-goal')) {
            const button = e.target.closest('.delete-goal');
            pendingDeleteGoalId = button.dataset.goalId;
            pendingDeleteButton = button;
            deleteModal.show();
        }
    });

    // Handle delete confirmation
    document.getElementById('confirmDeleteGoal').addEventListener('click', async function() {
        if (!pendingDeleteGoalId) return;
        
        try {
            const response = await api.delete(`/delete_progression_goal/${pendingDeleteGoalId}`, { showErrorToast: false });
            
            deleteModal.hide();
            showToast('success', getProgressionSuccessMessage(response, 'Goal deleted successfully'));
            // Remove the row from the table
            if (pendingDeleteButton) {
                pendingDeleteButton.closest('tr').remove();
            }
        } catch (error) {
            console.error('Error deleting goal:', error);
            deleteModal.hide();
            showToast('Failed to delete goal: ' + error.message, true);
        } finally {
            pendingDeleteGoalId = null;
            pendingDeleteButton = null;
        }
    });

    // Handle goal completion
    document.addEventListener('click', async function(e) {
        if (e.target.closest('.complete-goal')) {
            const button = e.target.closest('.complete-goal');
            const goalId = button.dataset.goalId;
            
            try {
                const response = await api.post(`/complete_progression_goal/${goalId}`, {}, { showErrorToast: false });
                
                showToast('success', getProgressionSuccessMessage(response, 'Goal marked as completed!'));
                // Update the row to show completed status
                const row = button.closest('tr');
                const statusCell = row.querySelector('.badge');
                if (statusCell) {
                    statusCell.classList.remove('bg-primary');
                    statusCell.classList.add('bg-success');
                    statusCell.textContent = 'Completed';
                }
                // Remove the complete button
                button.remove();
            } catch (error) {
                console.error('Error completing goal:', error);
                showToast('Failed to complete goal: ' + error.message, true);
            }
        }
    });
} 

function createSuggestionCard(suggestion) {
    return `
        <div class="col-md-6 col-lg-3 mb-4">
            <div class="card suggestion-card h-100">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">${suggestion.title}</h5>
                    <p class="card-text">${suggestion.description}</p>
                    <button class="btn btn-primary set-goal-btn mt-auto" 
                            data-goal-type="${suggestion.type}"
                            onclick="openGoalModal(this)">
                        ${suggestion.action}
                    </button>
                </div>
            </div>
        </div>
    `;
}

function openGoalModal(button) {
    const goalType = button.getAttribute('data-goal-type');
    const modalTitle = document.getElementById('goalModalLabel');
    const currentValueInput = document.getElementById('currentValue');
    const targetValueInput = document.getElementById('targetValue');
    
    // Set appropriate labels and placeholders based on goal type
    switch(goalType) {
        case 'weight':
            modalTitle.textContent = 'Set Weight Goal';
            currentValueInput.placeholder = 'Current weight (kg)';
            targetValueInput.placeholder = 'Target weight (kg)';
            break;
        case 'reps':
            modalTitle.textContent = 'Set Repetition Goal';
            currentValueInput.placeholder = 'Current reps';
            targetValueInput.placeholder = 'Target reps';
            break;
        case 'sets':
            modalTitle.textContent = 'Set Volume Goal';
            currentValueInput.placeholder = 'Current sets';
            targetValueInput.placeholder = 'Target sets';
            break;
        case 'technique':
            modalTitle.textContent = 'Set Technique Goal';
            currentValueInput.placeholder = 'Current proficiency (1-10)';
            targetValueInput.placeholder = 'Target proficiency (1-10)';
            break;
    }
    
    // Get and set current value
    getCurrentValue(goalType);
} 
