import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';
import { updateCachedExercise, updateRowMetadata } from './workout-plan-table.js';
import { buildReplacePayload, resolveSwapErrorToast } from './workout-plan-helpers.js';

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
 * Handles the swap/replace exercise action
 * @param {number} exerciseId - The user_selection.id of the exercise to swap
 * @param {string} currentExerciseName - The current exercise name (for display)
 */
export async function handleSwapExercise(exerciseId, currentExerciseName) {
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
