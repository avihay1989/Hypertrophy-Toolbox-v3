import { showToast } from './toast.js';
import { fetchWorkoutPlan, resetWorkoutControlsToDefaults } from './workout-plan.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';
import { api } from './fetch-wrapper.js';

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
        const result = await api.post("/remove_exercise", { id: exerciseId }, {
            headers: { "Content-Type": "application/json" },
            showLoading: false,
            showErrorToast: false,
            useDefaultHeaders: false
        });
        showToast(result.message || "Exercise removed successfully!");
        fetchWorkoutPlan();
        notifyVolumeAffectingPlanChange('remove-exercise');
    } catch (error) {
        console.error("Error removing exercise:", error);
        showToast(`Unable to remove exercise: ${error.message}`, true);
    } finally {
        deletingExercises.delete(exerciseId);
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

        const result = await api.post('/clear_workout_plan', null, {
            headers: { 'Content-Type': 'application/json' },
            showLoading: false,
            showErrorToast: false,
            useDefaultHeaders: false
        });
        showToast(result.message || 'Workout plan cleared successfully!');
        fetchWorkoutPlan(); // Refresh the table to show empty state
        notifyVolumeAffectingPlanChange('clear-workout-plan');
        // KI-005 criterion 4: Clear Plan resets the six Workout Controls to
        // the pinned template defaults (under suppression) and removes the
        // stored record LAST, leaving the key absent (OWNER-1.4).
        resetWorkoutControlsToDefaults();
    } catch (error) {
        console.error('Error clearing workout plan:', error);
        showToast(`Unable to clear workout plan: ${error.message}`, true);
    }
}
