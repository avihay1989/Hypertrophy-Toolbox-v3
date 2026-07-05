import { showToast } from './toast.js';
import { fetchWorkoutPlan } from './workout-plan.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';

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
