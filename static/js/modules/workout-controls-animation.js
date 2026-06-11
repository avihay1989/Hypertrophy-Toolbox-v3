/**
 * Workout Controls Animation Module
 * 
 * Provides "value changed" animation and highlight effects for workout control inputs.
 * Triggers on spinner clicks, keyboard input, and paste events.
 */

const ANIMATION_DURATION = 300; // milliseconds

// Target input IDs for workout controls
const WORKOUT_CONTROL_IDS = [
    'weight',
    'sets',
    'rir',
    'rpe',
    'min_rep',
    'max_rep_range'
];

/**
 * Triggers the value-changed animation on an input element.
 * Removes and re-adds the class to restart animation on rapid changes.
 * @param {HTMLElement} inputElement - The input element to animate
 */
function triggerValueChangedAnimation(inputElement) {
    if (!inputElement) return;
    
    // Remove class first to allow re-triggering animation
    inputElement.classList.remove('value-changed');
    
    // Force reflow to ensure animation restarts
    void inputElement.offsetWidth;
    
    // Add the animation class
    inputElement.classList.add('value-changed');
    
    // Remove the class after animation completes
    setTimeout(() => {
        inputElement.classList.remove('value-changed');
    }, ANIMATION_DURATION);
}

/**
 * Handles input events (typing, delete, paste) on workout control inputs.
 * @param {Event} event - The input event
 */
function handleInputChange(event) {
    triggerValueChangedAnimation(event.target);
}

/**
 * Handles mouseup events on number input spinners.
 * This catches clicks on the up/down spinner arrows.
 * @param {Event} event - The mouseup event
 */
function handleSpinnerClick(event) {
    const input = event.target;
    
    // Only trigger for number inputs with spinners
    if (input.type === 'number') {
        // Small delay to ensure the value has changed
        setTimeout(() => {
            triggerValueChangedAnimation(input);
        }, 10);
    }
}

/**
 * Handles wheel events on number inputs (scroll to change value).
 * @param {Event} event - The wheel event
 */
function handleWheelChange(event) {
    const input = event.target;
    
    // Only trigger for focused number inputs
    if (input.type === 'number' && document.activeElement === input) {
        setTimeout(() => {
            triggerValueChangedAnimation(input);
        }, 10);
    }
}

/**
 * Handles keyboard events for arrow up/down on number inputs.
 * @param {Event} event - The keydown event
 */
function handleKeyboardChange(event) {
    const input = event.target;
    
    // Only trigger for arrow keys on number inputs
    if (input.type === 'number' && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
        setTimeout(() => {
            triggerValueChangedAnimation(input);
        }, 10);
    }
}

/**
 * Initializes event listeners for a single workout control input.
 * @param {string} inputId - The ID of the input element
 */
function initializeInputAnimation(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    // Store initial value to detect changes
    let previousValue = input.value;
    
    // Input event - fires on typing, paste, etc.
    input.addEventListener('input', (event) => {
        // Only trigger if value actually changed
        if (input.value !== previousValue) {
            previousValue = input.value;
            handleInputChange(event);
        }
    });
    
    // Mouseup on the input (catches spinner clicks)
    input.addEventListener('mouseup', (event) => {
        // Check if value changed after mouse interaction
        if (input.value !== previousValue) {
            previousValue = input.value;
            handleSpinnerClick(event);
        }
    });
    
    // Wheel event for scroll-to-change
    input.addEventListener('wheel', (event) => {
        // Small delay to check value after wheel
        setTimeout(() => {
            if (input.value !== previousValue) {
                previousValue = input.value;
                triggerValueChangedAnimation(input);
            }
        }, 50);
    }, { passive: true });
    
    // Keyboard arrow up/down
    input.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
            const currentVal = input.value;
            // Small delay to let the value update
            setTimeout(() => {
                if (input.value !== currentVal) {
                    previousValue = input.value;
                    triggerValueChangedAnimation(input);
                }
            }, 10);
        }
    });
    
    // Change event as fallback (fires on blur after value change)
    input.addEventListener('change', (event) => {
        if (input.value !== previousValue) {
            previousValue = input.value;
            triggerValueChangedAnimation(input);
        }
    });
}

/**
 * Initializes the workout controls animation module.
 * Sets up event listeners on all workout control inputs.
 */
export function initializeWorkoutControlsAnimation() {
    // Only initialize on workout plan page
    const workoutControlsPanel = document.querySelector('[data-section="controls"]');
    if (!workoutControlsPanel) return;
    
    WORKOUT_CONTROL_IDS.forEach(inputId => {
        initializeInputAnimation(inputId);
    });
    
    console.log('[WorkoutControlsAnimation] Initialized value-changed animations for workout controls');
}
