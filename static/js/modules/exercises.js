import { showToast } from './toast.js';
import { fetchWorkoutPlan } from './workout-plan.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';

// Debounce flag to prevent duplicate submissions
let isSubmitting = false;

/**
 * Validate exercise form values for edge cases and boundaries
 * @param {Object} values - Object containing form values
 * @returns {string|null} Error message or null if valid
 */
function validateExerciseValues(values) {
    const { sets, minRep, maxRep, weight, rir, rpe } = values;
    
    // Parse values
    const setsNum = parseInt(sets);
    const minRepNum = parseInt(minRep);
    const maxRepNum = parseInt(maxRep);
    const weightNum = parseFloat(weight);
    const rirNum = rir ? parseInt(rir) : null;
    const rpeNum = rpe ? parseFloat(rpe) : null;
    
    // Validate sets (must be positive integer)
    if (isNaN(setsNum) || setsNum <= 0) {
        return 'Sets must be a positive number';
    }
    if (setsNum > 20) {
        return 'Sets should not exceed 20 per exercise';
    }
    
    // Validate rep range (must be positive)
    if (isNaN(minRepNum) || minRepNum <= 0) {
        return 'Min reps must be a positive number';
    }
    if (isNaN(maxRepNum) || maxRepNum <= 0) {
        return 'Max reps must be a positive number';
    }
    
    // Validate min <= max
    if (minRepNum > maxRepNum) {
        return 'Min reps cannot exceed max reps';
    }
    
    // Validate reasonable rep ranges
    if (minRepNum > 100 || maxRepNum > 100) {
        return 'Rep range seems unrealistic (max 100)';
    }
    
    // Validate weight (allow 0 for bodyweight, but not negative)
    if (isNaN(weightNum) || weightNum < 0) {
        return 'Weight cannot be negative';
    }
    if (weightNum > 2000) {
        return 'Weight seems unrealistic (max 2000)';
    }
    
    // Validate RIR if provided (0-10 scale, typical range 0-4)
    if (rirNum !== null) {
        if (isNaN(rirNum) || rirNum < 0) {
            return 'RIR cannot be negative';
        }
        if (rirNum > 10) {
            return 'RIR should not exceed 10';
        }
    }
    
    // Validate RPE if provided (1-10 scale)
    if (rpeNum !== null) {
        if (isNaN(rpeNum) || rpeNum < 1) {
            return 'RPE must be at least 1';
        }
        if (rpeNum > 10) {
            return 'RPE cannot exceed 10 (scale is 1-10)';
        }
    }
    
    return null; // No validation errors
}

export function addExercise() {
    console.log('addExercise function called');
    
    // Debounce: Prevent duplicate submissions
    if (isSubmitting) {
        console.log('Submission already in progress, ignoring duplicate click');
        return;
    }

    const exercise = document.getElementById('exercise')?.value;
    const routine = document.getElementById('routine')?.value;
    const sets = document.getElementById('sets')?.value;
    const minRepRange = document.getElementById('min_rep')?.value;
    const maxRepRange = document.getElementById('max_rep_range')?.value;
    const rir = document.getElementById('rir')?.value;
    const weight = document.getElementById('weight')?.value;
    const rpe = document.getElementById('rpe')?.value;

    // Validate required fields
    if (!exercise || !routine || !sets || !minRepRange || !maxRepRange || !weight) {
        showToast('Please fill in all required fields', true);
        return;
    }
    
    // Validate exercise selection (not just placeholder)
    if (exercise === '' || exercise.toLowerCase().includes('select')) {
        showToast('Please select an exercise', true);
        return;
    }

    // Validate boundary values
    const validationError = validateExerciseValues({
        sets,
        minRep: minRepRange,
        maxRep: maxRepRange,
        weight,
        rir,
        rpe
    });
    
    if (validationError) {
        showToast(validationError, true);
        return;
    }

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

    // Set submission flag before async call
    isSubmitting = true;
    
    // Disable button visually
    const addBtn = document.getElementById('add_exercise_btn');
    if (addBtn) {
        addBtn.disabled = true;
        addBtn.classList.add('loading');
    }
    
    sendExerciseData(exerciseData);
}

async function sendExerciseData(exerciseData) {
    const addBtn = document.getElementById('add_exercise_btn');
    
    try {
        const response = await fetch('/add_exercise', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(exerciseData)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to add exercise');
        }
        
        showToast('Exercise added successfully');
        fetchWorkoutPlan();
        notifyVolumeAffectingPlanChange('legacy-add-exercise');
        resetFormFields();
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Failed to add exercise', true);
    } finally {
        // Reset submission flag
        isSubmitting = false;
        
        // Re-enable button
        if (addBtn) {
            addBtn.disabled = false;
            addBtn.classList.remove('loading');
        }
    }
}

// Track exercises being deleted to prevent double-delete
const deletingExercises = new Set();

export async function removeExercise(exerciseId) {
    if (!exerciseId) {
        console.error("Error: exercise ID is required to remove an exercise.");
        showToast("Exercise ID is missing. Unable to remove exercise.", true);
        return;
    }
    
    // Prevent duplicate delete operations
    if (deletingExercises.has(exerciseId)) {
        console.log('Delete already in progress for exercise:', exerciseId);
        return;
    }
    
    deletingExercises.add(exerciseId);

    try {
        const response = await fetch("/remove_exercise", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: exerciseId }),
        });

        const result = await response.json();
        
        if (response.ok) {
            showToast(result.message || "Exercise removed successfully!");
            fetchWorkoutPlan();
            notifyVolumeAffectingPlanChange('remove-exercise');
        } else {
            throw new Error(result.message || "Failed to remove exercise");
        }
    } catch (error) {
        console.error("Error removing exercise:", error);
        showToast(`Unable to remove exercise: ${error.message}`, true);
    } finally {
        deletingExercises.delete(exerciseId);
    }
}

function resetFormFields() {
    document.getElementById('sets').value = '1';
    document.getElementById('rir').value = '0';
    document.getElementById('weight').value = '100';
    document.getElementById('min_rep').value = '3';
    document.getElementById('max_rep_range').value = '5';
    if (document.getElementById('rpe')) {
        document.getElementById('rpe').value = '';
    }
}

export async function clearWorkoutPlan() {
    try {
        // Close the modal
        const modal = document.getElementById('clearPlanModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }

        const response = await fetch('/clear_workout_plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        
        if (response.ok) {
            showToast(result.message || 'Workout plan cleared successfully!');
            fetchWorkoutPlan(); // Refresh the table to show empty state
            notifyVolumeAffectingPlanChange('clear-workout-plan');
        } else {
            throw new Error(result.error?.message || result.message || 'Failed to clear workout plan');
        }
    } catch (error) {
        console.error('Error clearing workout plan:', error);
        showToast(`Unable to clear workout plan: ${error.message}`, true);
    }
}
